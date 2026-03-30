"""
DiplomaUpdater — importeert diploma's van kinderopvang-werkt.nl API.

Logica:
- Haalt alle diplomas op van de API
- Upsert in diplomacheck_diploma tabel
- Slaat over als < 180 dagen geleden gerund (via airflow_sentinel tabel)
- Rollback als diplomas > 10% dalen

Wordt aangeroepen vanuit dags/diploma_dag.py.
"""

import logging
import re
from datetime import date

import requests

from db.connection import get_connection

logger = logging.getLogger(__name__)

API_URL = "https://www.kinderopvang-werkt.nl/possible-diplomas?time=0"
SENTINEL_KEY = "diploma_last_run"
INTERVAL_DAYS = 180

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.kinderopvang-werkt.nl/",
}

LEVEL_RE = re.compile(r"\s*\([^)]+\)\s*$")


def parse_level(raw: str) -> str:
    """Extraheer MBO/HBO/WO niveau uit een ruwe string."""
    r = raw.lower().strip()
    if "mbo-3" in r or "mbo 3" in r or r == "mbo3":
        return "mbo3"
    if "mbo-4" in r or "mbo 4" in r or r == "mbo4":
        return "mbo4"
    if "mbo-2" in r or "mbo 2" in r or r == "mbo2":
        return "mbo2"
    if "master" in r or "universitair" in r or r == "wo":
        return "wo"
    return "hbo"


def parse_status(val: str) -> str:
    """Vertaal API status code naar leesbare string."""
    if val == "1":
        return "direct"
    if val == "2":
        return "proof_required"
    return "not_qualified"


def parse_diploma_entries(raw_list: list) -> list[dict]:
    """
    Parseer ruwe API response naar diploma-entries.
    Geeft lijst van {name, level, kdv_status, bso_status, notes} dicts.
    """
    entries = []
    for item in raw_list:
        title = item.get("title", "").strip()
        if not title:
            continue
        m = re.search(r"\(([^)]+)\)\s*$", title)
        level_raw = m.group(1) if m else ""
        level = parse_level(level_raw)
        name = LEVEL_RE.sub("", title).strip()
        if not name:
            continue
        entries.append({
            "name": name,
            "level": level,
            "kdv_status": parse_status(item.get("field_dagopvang", "0")),
            "bso_status": parse_status(item.get("field_buitenschoolse_opvang", "0")),
            "notes": f"API nid={item.get('nid', '')}",
        })
    return entries


def _get_last_run(cur) -> date | None:
    cur.execute(
        "SELECT value FROM airflow_sentinel WHERE key = %s",
        (SENTINEL_KEY,)
    )
    row = cur.fetchone()
    if row:
        try:
            return date.fromisoformat(row[0][:10])
        except Exception:
            pass
    return None


def _set_last_run(cur):
    cur.execute(
        """
        INSERT INTO airflow_sentinel (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """,
        (SENTINEL_KEY, date.today().isoformat()),
    )


def run_diploma_update(force: bool = False) -> dict:
    """
    Volledige diploma update cyclus:
    1. Controleer sentinel (throttle 180 dagen)
    2. Haal data op van API
    3. Parseer entries
    4. Upsert in DB in transactie
    5. Valideer (rollback als >10% daling)
    6. Sla sentinel op

    Geeft stats dict terug: {created, updated, total} of {skipped: True}.
    """
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()

            # Zorg dat sentinel tabel bestaat
            cur.execute("""
                CREATE TABLE IF NOT EXISTS airflow_sentinel (
                    key        VARCHAR(100) PRIMARY KEY,
                    value      TEXT NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            last_run = _get_last_run(cur)
            days_ago = (date.today() - last_run).days if last_run else None

            if not force and days_ago is not None and days_ago < INTERVAL_DAYS:
                logger.info(
                    f"Diploma update overgeslagen: laatste run {days_ago} dagen geleden "
                    f"(threshold {INTERVAL_DAYS} dagen). Gebruik force=True om te forceren."
                )
                return {"skipped": True, "days_ago": days_ago}

            logger.info(
                f"Diploma update gestart. Vorige run: {last_run} ({days_ago}d geleden)"
                if last_run else "Diploma update gestart. Eerste run."
            )

            # Haal data op van API
            resp = requests.get(API_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise ValueError("API gaf geen success=true")

            raw_list = data["diplomas"]
            logger.info(f"Ontvangen: {len(raw_list)} items van API")

            entries = parse_diploma_entries(raw_list)
            logger.info(f"Geparseerd: {len(entries)} diploma-entries")

            # Tel huidige diplomas voor validatie
            cur.execute("SELECT COUNT(*) FROM diplomacheck_diploma")
            count_before = cur.fetchone()[0]

            # Upsert
            created = updated = 0
            for e in entries:
                cur.execute(
                    "SELECT id FROM diplomacheck_diploma WHERE name = %s AND level = %s",
                    (e["name"], e["level"]),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE diplomacheck_diploma
                        SET kdv_status = %s, bso_status = %s, notes = %s, is_active = TRUE
                        WHERE id = %s
                        """,
                        (e["kdv_status"], e["bso_status"], e["notes"], existing[0]),
                    )
                    updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO diplomacheck_diploma
                            (name, level, kdv_status, bso_status, notes, crebo,
                             qualifying_roles, qualifying_institution_types,
                             is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, '', '[]', '[]', TRUE, NOW(), NOW())
                        """,
                        (e["name"], e["level"], e["kdv_status"], e["bso_status"], e["notes"]),
                    )
                    created += 1

            # Validatie: rollback als >10% daling
            cur.execute("SELECT COUNT(*) FROM diplomacheck_diploma")
            count_after = cur.fetchone()[0]
            if count_before > 0 and count_after < count_before * 0.9:
                raise ValueError(
                    f"ROLLBACK: diplomas daalden van {count_before} naar {count_after}. "
                    "Transactie teruggedraaid."
                )

            _set_last_run(cur)

            stats = {"created": created, "updated": updated, "total": count_after}
            logger.info(f"Diploma update klaar: {stats}")
            return stats

    finally:
        conn.close()
