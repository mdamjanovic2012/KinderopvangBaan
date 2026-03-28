"""
DAG: diploma_update
Importeert diploma's van kinderopvang-werkt.nl API.
Draait max 1x per 180 dagen (sentinel in jobs_geocodedlocation schemaontwerp
slaat de datum op in een aparte controletabel, zie hieronder).

Vervanger van: backend/startup.sh update_diplomas + diploma-update.yml pipeline.
"""

import logging
import re
from datetime import date, datetime, timedelta

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


def _parse_level(raw: str) -> str:
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


def _parse_status(val: str) -> str:
    if val == "1":
        return "direct"
    if val == "2":
        return "proof_required"
    return "not_qualified"


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


def run_diploma_update(force: bool = False):
    """
    Importeert diplomas van kinderopvang-werkt.nl in de diplomacheck_diploma tabel.
    Slaat over als < 180 dagen geleden, tenzij force=True.
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

            logger.info(f"Diploma update gestart. Vorige run: {last_run} ({days_ago}d geleden)" if last_run
                        else "Diploma update gestart. Eerste run.")

            # Haal data op van API
            resp = requests.get(API_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise ValueError("API gaf geen success=true")

            raw_list = data["diplomas"]
            logger.info(f"Ontvangen: {len(raw_list)} items van API")

            # Parse entries
            entries = []
            for item in raw_list:
                title = item.get("title", "").strip()
                if not title:
                    continue
                m = re.search(r"\(([^)]+)\)\s*$", title)
                level_raw = m.group(1) if m else ""
                level = _parse_level(level_raw)
                name = LEVEL_RE.sub("", title).strip()
                if not name:
                    continue
                entries.append({
                    "name": name,
                    "level": level,
                    "kdv_status": _parse_status(item.get("field_dagopvang", "0")),
                    "bso_status": _parse_status(item.get("field_buitenschoolse_opvang", "0")),
                    "notes": f"API nid={item.get('nid', '')}",
                })

            logger.info(f"Geparseerd: {len(entries)} diploma-entries")

            # Tel huidige diplomas voor validatie
            cur.execute("SELECT COUNT(*) FROM diplomacheck_diploma")
            count_before = cur.fetchone()[0]

            # Upsert in transactie
            created = updated = 0
            for e in entries:
                cur.execute(
                    """
                    SELECT id FROM diplomacheck_diploma WHERE name = %s AND level = %s
                    """,
                    (e["name"], e["level"]),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE diplomacheck_diploma
                        SET kdv_status = %s, bso_status = %s, notes = %s,
                            is_active = TRUE
                        WHERE id = %s
                        """,
                        (e["kdv_status"], e["bso_status"], e["notes"], existing[0]),
                    )
                    updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO diplomacheck_diploma
                            (name, level, kdv_status, bso_status, notes, crebo, is_active)
                        VALUES (%s, %s, %s, %s, %s, '', TRUE)
                        """,
                        (e["name"], e["level"], e["kdv_status"], e["bso_status"], e["notes"]),
                    )
                    created += 1

            # Validatie
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


# ── Airflow DAG ───────────────────────────────────────────────────────────────

from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG(
    dag_id="diploma_update",
    description="Importeert diploma's van kinderopvang-werkt.nl (max 1x per 180 dagen)",
    schedule="0 5 * * 1",        # elke maandag om 05:00 — check of update nodig is
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
        "execution_timeout": timedelta(minutes=20),
    },
    tags=["diplomas"],
) as dag:

    update = PythonOperator(
        task_id="run_diploma_update",
        python_callable=run_diploma_update,
        op_kwargs={"force": False},
    )
