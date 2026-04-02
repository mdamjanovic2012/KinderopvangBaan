"""
Link validator — async controle van alle actieve job-URLs.

Aanpak:
  • Server-side cursor: rijen worden in chunks van CHUNK_SIZE uit de DB gestream
    zodat nooit de volledige dataset in geheugen staat.
  • aiohttp + asyncio.gather: binnen elke chunk worden URLs parallel gecheckt
    (max CONCURRENCY tegelijk, max DOMAIN_CONCURRENCY per domein).
  • Dode URLs worden per chunk direct naar de DB geflushed (geen opbouw in geheugen).

Definitie "dode URL":
  • HTTP 404, 410, 400
  • Redirect naar root / homepage (pad eindigt op bekende homepage-paden)
  • DNS/verbindingsfout of timeout

Typische runtime: ~5 min voor 10 000 URLs bij CONCURRENCY=30.
"""

import asyncio
import logging
from collections import defaultdict
from urllib.parse import urlparse

import aiohttp
from psycopg2.extras import execute_values

from db.connection import get_connection

logger = logging.getLogger(__name__)

# ── Tuning ────────────────────────────────────────────────────────────────────

CONCURRENCY      = 30    # max gelijktijdige HTTP-verbindingen (totaal)
DOMAIN_CONCURRENCY = 3   # max per domein (beleefd crawlen)
CHUNK_SIZE       = 500   # rijen per DB-fetch en async-batch
REQUEST_TIMEOUT  = aiohttp.ClientTimeout(total=12, connect=5)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9",
}

DEAD_STATUS_CODES = {400, 404, 410}

# Paden die wijzen op een homepage-redirect (geen specifieke vacature)
HOMEPAGE_PATHS = frozenset({
    "", "/", "/nl", "/nl/",
    "/vacatures", "/vacatures/",
    "/jobs", "/jobs/",
    "/werken-bij", "/werken-bij/",
    "/carriere", "/carriere/",
})


# ── Async HTTP check ──────────────────────────────────────────────────────────

async def _check_url(
    session: aiohttp.ClientSession,
    global_sem: asyncio.Semaphore,
    domain_sems: dict,
    job_id: int,
    url: str,
) -> tuple[int, str, bool, str]:
    """
    Controleer één URL. Geeft (job_id, url, is_dead, reden) terug.
    Gooit nooit een exception — fouten worden omgezet naar (True, reden).
    """
    domain = urlparse(url).netloc
    if domain not in domain_sems:
        domain_sems[domain] = asyncio.Semaphore(DOMAIN_CONCURRENCY)

    async with global_sem, domain_sems[domain]:
        try:
            # Stap 1: HEAD-request (snel, geen body)
            async with session.head(url, allow_redirects=True) as resp:
                if resp.status == 405:
                    # HEAD niet toegestaan → GET zonder body lezen
                    async with session.get(url, allow_redirects=True) as gresp:
                        status    = gresp.status
                        final_url = str(gresp.url)
                else:
                    status    = resp.status
                    final_url = str(resp.url)

            if status in DEAD_STATUS_CODES:
                return job_id, url, True, f"HTTP {status}"

            # Stap 2: homepage-redirect detecteren
            path = urlparse(final_url).path.rstrip("/")
            if path in HOMEPAGE_PATHS:
                return job_id, url, True, f"redirect naar homepage ({final_url})"

            return job_id, url, False, ""

        except aiohttp.ClientConnectorError:
            return job_id, url, True, "DNS/verbindingsfout"
        except asyncio.TimeoutError:
            return job_id, url, True, "timeout (12s)"
        except aiohttp.ClientResponseError as exc:
            if exc.status in DEAD_STATUS_CODES:
                return job_id, url, True, f"HTTP {exc.status}"
            return job_id, url, False, ""
        except Exception as exc:
            logger.debug(f"[link-validator] onverwacht bij {url}: {exc}")
            return job_id, url, False, ""  # twijfelgeval → niet blacklisten


async def _process_chunk(
    session: aiohttp.ClientSession,
    global_sem: asyncio.Semaphore,
    domain_sems: dict,
    rows: list[tuple[int, str]],
) -> list[tuple[int, str, str]]:
    """
    Controleer een chunk van (job_id, url)-paren parallel.
    Geeft lijst van (job_id, url, reden) voor dode URLs terug.
    """
    tasks = [
        asyncio.create_task(_check_url(session, global_sem, domain_sems, jid, url))
        for jid, url in rows
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return [(jid, url, reason) for jid, url, is_dead, reason in results if is_dead]


# ── DB helpers ────────────────────────────────────────────────────────────────

def _ensure_blacklist_table(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs_blacklisted_url (
            id             SERIAL PRIMARY KEY,
            url            TEXT        NOT NULL UNIQUE,
            reason         TEXT        NOT NULL,
            blacklisted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _flush_dead(conn, dead: list[tuple[int, str, str]]) -> None:
    """Batch-update DB: blacklist + is_expired voor dode URLs."""
    if not dead:
        return
    job_ids   = [d[0] for d in dead]
    url_rows  = [(d[1], d[2]) for d in dead]

    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO jobs_blacklisted_url (url, reason) VALUES %s "
            "ON CONFLICT (url) DO NOTHING",
            url_rows,
        )
        cur.execute(
            "UPDATE jobs_job SET is_expired = TRUE, updated_at = NOW() "
            "WHERE id = ANY(%s)",
            (job_ids,),
        )
    conn.commit()
    logger.info(f"[link-validator] {len(dead)} dode URLs opgeslagen")


# ── Hoofdfunctie ──────────────────────────────────────────────────────────────

def run_link_validation() -> dict:
    """
    Controleer alle actieve, niet-verlopen job-URLs en blacklist dode links.

    Gebruikt een server-side cursor om geheugengebruik te beperken:
    slechts CHUNK_SIZE rijen staan tegelijk in geheugen.

    Returns:
        dict met "checked", "blacklisted", "errors"
    """
    stats = {"checked": 0, "blacklisted": 0, "errors": 0}

    conn = get_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            _ensure_blacklist_table(cur)
        conn.commit()

        # Server-side cursor: DB streamt CHUNK_SIZE rijen per keer
        with conn.cursor(name="lv_cursor") as cur:
            cur.itersize = CHUNK_SIZE
            cur.execute("""
                SELECT j.id, j.source_url
                FROM   jobs_job j
                WHERE  j.is_expired = FALSE
                  AND  j.is_active  = TRUE
                  AND  NOT EXISTS (
                      SELECT 1 FROM jobs_blacklisted_url b
                      WHERE  b.url = j.source_url
                  )
                ORDER BY j.id
            """)

            connector = aiohttp.TCPConnector(
                limit=CONCURRENCY,
                ttl_dns_cache=300,   # cache DNS voor 5 min
                enable_cleanup_closed=True,
            )

            async def run_all():
                global_sem  = asyncio.Semaphore(CONCURRENCY)
                domain_sems: dict = {}

                async with aiohttp.ClientSession(
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    connector=connector,
                    connector_owner=False,
                ) as session:
                    while True:
                        chunk = cur.fetchmany(CHUNK_SIZE)
                        if not chunk:
                            break

                        stats["checked"] += len(chunk)
                        logger.info(
                            f"[link-validator] chunk {stats['checked']} URLs verwerkt..."
                        )

                        dead = await _process_chunk(session, global_sem, domain_sems, chunk)
                        if dead:
                            _flush_dead(conn, dead)
                            stats["blacklisted"] += len(dead)

            asyncio.run(run_all())
            connector.close()

    except Exception as exc:
        logger.error(f"[link-validator] kritieke fout: {exc}", exc_info=True)
        stats["errors"] += 1
        conn.rollback()
        raise
    finally:
        conn.close()

    logger.info(
        f"[link-validator] klaar — "
        f"gecontroleerd: {stats['checked']}, "
        f"geblacklisted: {stats['blacklisted']}"
    )
    return stats
