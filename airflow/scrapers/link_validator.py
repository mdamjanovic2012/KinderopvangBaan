"""
Link validator — controleert alle actieve job-URLs en blacklisted dode links.

Wat doet het:
1. Maak de blacklist-tabel aan als die niet bestaat
2. Haal alle actieve, niet-verlopen jobs op
3. HEAD-request voor elke URL (met User-Agent, volg redirects)
4. Als de URL dood is (404, 410, DNS-fout, timeout) → blacklist + is_expired=True
5. Als de URL redirect naar een homepage (geen /vacature/ in pad) → ook blacklist

Definitie "dode URL":
- HTTP 404, 410, 400, 403 (job-specifiek)
- ConnectionError / Timeout
- Redirect naar root / homepage zonder vacature-pad

Statistieken worden teruggegeven als dict.
"""

import logging
import time

import requests

from db.connection import get_connection

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9",
}

# HTTP-statuscodes die een dode vacature-link aangeven
DEAD_STATUS_CODES = {404, 410, 400}

# Paden die op een homepage-redirect wijzen (geen specifieke vacature)
HOMEPAGE_PATHS = {"", "/", "/nl", "/nl/", "/vacatures", "/vacatures/", "/jobs", "/jobs/"}


def _ensure_blacklist_table(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs_blacklisted_url (
            id          SERIAL PRIMARY KEY,
            url         TEXT    NOT NULL UNIQUE,
            reason      TEXT    NOT NULL,
            blacklisted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _is_dead_url(url: str) -> tuple[bool, str]:
    """
    Stuur een HEAD-request (val terug op GET bij 405).
    Geeft (is_dead, reden) terug.
    """
    try:
        resp = requests.head(
            url,
            headers=HEADERS,
            timeout=10,
            allow_redirects=True,
        )
        # HEAD niet toegestaan → probeer GET
        if resp.status_code == 405:
            resp = requests.get(
                url,
                headers=HEADERS,
                timeout=10,
                allow_redirects=True,
                stream=True,  # laad alleen headers, geen body
            )
            resp.close()

        if resp.status_code in DEAD_STATUS_CODES:
            return True, f"HTTP {resp.status_code}"

        # Controleer of er naar homepage omgeleid is
        final_path = resp.url.rstrip("/").split("?")[0]
        from urllib.parse import urlparse
        parsed = urlparse(final_path)
        if parsed.path in HOMEPAGE_PATHS or parsed.path == "":
            return True, f"redirect naar homepage ({resp.url})"

        return False, ""

    except requests.exceptions.ConnectionError as exc:
        return True, f"DNS/connectiefout: {exc}"
    except requests.exceptions.Timeout:
        return True, "timeout (10s)"
    except Exception as exc:
        logger.warning(f"Onverwachte fout bij {url}: {exc}")
        return False, ""  # twijfelgeval → niet blacklisten


def run_link_validation(batch_size: int = 200, sleep_between: float = 0.5) -> dict:
    """
    Hoofdfunctie: controleer alle actieve job-URLs en blacklist dode links.

    Args:
        batch_size: aantal jobs per DB-batch (voor geheugen)
        sleep_between: seconden wachten tussen requests (beleefd crawlen)

    Returns:
        dict met statistieken: checked, blacklisted, errors
    """
    stats = {"checked": 0, "blacklisted": 0, "errors": 0}

    conn = get_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            _ensure_blacklist_table(cur)
            conn.commit()

            # Haal alle actieve, niet-verlopen jobs op die nog niet geblacklisted zijn
            cur.execute("""
                SELECT j.id, j.source_url
                FROM   jobs_job j
                WHERE  j.is_expired  = FALSE
                  AND  j.is_active   = TRUE
                  AND  j.source_url NOT IN (
                           SELECT url FROM jobs_blacklisted_url
                       )
                ORDER BY j.id
            """)
            rows = cur.fetchall()

        logger.info(f"[link-validator] {len(rows)} URLs te controleren")

        dead_ids: list[int] = []
        dead_urls: list[tuple[str, str]] = []  # (url, reden)

        for job_id, url in rows:
            stats["checked"] += 1
            is_dead, reason = _is_dead_url(url)

            if is_dead:
                logger.info(f"[link-validator] DOOD: {url} — {reason}")
                dead_ids.append(job_id)
                dead_urls.append((url, reason))

            time.sleep(sleep_between)

            # Tussentijds opslaan per 50 dode URLs (bij lange runs)
            if len(dead_ids) >= 50:
                _flush_dead(conn, dead_ids, dead_urls)
                stats["blacklisted"] += len(dead_ids)
                dead_ids.clear()
                dead_urls.clear()

        # Resterende opslaan
        if dead_ids:
            _flush_dead(conn, dead_ids, dead_urls)
            stats["blacklisted"] += len(dead_ids)

    except Exception as exc:
        logger.error(f"[link-validator] Kritieke fout: {exc}")
        stats["errors"] += 1
        conn.rollback()
        raise
    finally:
        conn.close()

    logger.info(
        f"[link-validator] Klaar — "
        f"gecontroleerd: {stats['checked']}, "
        f"geblacklisted: {stats['blacklisted']}"
    )
    return stats


def _flush_dead(conn, job_ids: list[int], url_reasons: list[tuple[str, str]]) -> None:
    """Sla dode URLs op in blacklist en markeer jobs als verlopen."""
    with conn.cursor() as cur:
        # Voeg toe aan blacklist (sla duplicaten over)
        for url, reason in url_reasons:
            cur.execute("""
                INSERT INTO jobs_blacklisted_url (url, reason)
                VALUES (%s, %s)
                ON CONFLICT (url) DO NOTHING
            """, (url, reason))

        # Markeer jobs als verlopen
        cur.execute("""
            UPDATE jobs_job
            SET    is_expired = TRUE,
                   updated_at = NOW()
            WHERE  id = ANY(%s)
        """, (job_ids,))

    conn.commit()
