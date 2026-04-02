"""
DAG: full_scrape
Volledige scrape-pipeline, 3× per week 's nachts (ma/wo/vr om 02:00).

Stappen:
  1. scrape_branches     — bijwerk vestigingen-adressen (PDOK geocoding)
  2. scrape_jobs_batch_* — alle 30 scrapers in batches van 5 (parallel per batch,
                           batches lopen sequentieel)
  3. validate_links      — controleer alle actieve job-URLs, blacklist dode links

Bestaande per-bedrijf DAGs blijven actief voor dagelijkse updates.
Deze DAG is bedoeld voor de wekelijkse volledige refresh + opschoning.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

# ── Scrapers: module → klasse (alphabetisch) ─────────────────────────────────

SCRAPERS = [
    ("bijdehandjes",    "scrapers.bijdehandjes",       "BijdeHandjesScraper"),
    ("bink",            "scrapers.bink",               "BinkScraper"),
    ("compananny",      "scrapers.compananny",         "CompaNannyScraper"),
    ("dak",             "scrapers.dak",                "DakScraper"),
    ("dichtbij",        "scrapers.dichtbij",           "DichtbijScraper"),
    ("doomijn",         "scrapers.doomijn",            "DoomijnScraper"),
    ("gro_up",          "scrapers.gro_up",             "GroUpScraper"),
    ("humankind",       "scrapers.humankind",          "HumankindScraper"),
    ("kanteel",         "scrapers.kanteel",            "KanteelScraper"),
    ("kibeo",           "scrapers.kibeo",              "KibeoScraper"),
    ("kids_first",      "scrapers.kids_first",         "KidsFirstScraper"),
    ("kinderdam",       "scrapers.kinderdam",          "KinderdamScraper"),
    ("kindergarden",    "scrapers.kindergarden",       "KindergardenScraper"),
    ("kinderwoud",      "scrapers.kinderwoud",         "KinderwoudScraper"),
    ("kion",            "scrapers.kion",               "KIONScraper"),
    ("ko_walcheren",    "scrapers.ko_walcheren",       "KOWalcherenScraper"),
    ("kober",           "scrapers.kober",              "KoberScraper"),
    ("mik",             "scrapers.mik",                "MIKScraper"),
    ("norlandia",       "scrapers.norlandia",          "NorlandiaScraper"),
    ("op_stoom",        "scrapers.op_stoom",           "OpStoomScraper"),
    ("partou",          "scrapers.partou",             "PartouScraper"),
    ("prokino",         "scrapers.prokino",            "ProkinoScraper"),
    ("samenwerkende_ko","scrapers.samenwerkende_ko",   "SamenwerkendeKOScraper"),
    ("sinne",           "scrapers.sinne",              "SinneScraper"),
    ("ska",             "scrapers.ska",                "SkaScraper"),
    ("spring",          "scrapers.spring_kinderopvang","SpringKinderopvangScraper"),
    ("tinteltuin",      "scrapers.tinteltuin",         "TintelTuinScraper"),
    ("twee_samen",      "scrapers.twee_samen",         "TweeSamenScraper"),
    ("wasko",           "scrapers.wasko",              "WaskoScraper"),
    ("wij_zijn_jong",   "scrapers.wij_zijn_jong",      "WijZijnJONGScraper"),
]

BATCH_SIZE = 5


def _make_scraper_callable(module: str, klass: str):
    """Geeft een callable terug die de scraper importeert en uitvoert."""
    def run():
        import importlib
        mod = importlib.import_module(module)
        scraper_cls = getattr(mod, klass)
        stats = scraper_cls().run()
        print(f"[{klass}] resultaat: {stats}")
        return stats
    run.__name__ = f"run_{klass.lower()}"
    return run


def run_branch_scrape():
    from scrapers.branches import run_vestigingen_scrape
    stats = run_vestigingen_scrape()
    print(f"[branches] resultaat: {stats}")
    return stats


def run_link_validation():
    from scrapers.link_validator import run_link_validation as validate
    stats = validate()
    print(f"[link-validator] resultaat: {stats}")
    return stats


# ── DAG definitie ─────────────────────────────────────────────────────────────

with DAG(
    dag_id="full_scrape",
    description="Volledige scrape-pipeline: branches → alle scrapers (5×5) → link-validatie",
    schedule="0 2 * * 1,3,5",   # ma/wo/vr om 02:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=45),
    },
    tags=["scraping", "full", "scheduled"],
    max_active_runs=1,           # nooit twee parallel-runs tegelijk
) as dag:

    # Stap 1: branches scrapen
    scrape_branches = PythonOperator(
        task_id="scrape_branches",
        python_callable=run_branch_scrape,
        execution_timeout=timedelta(minutes=30),
    )

    # Stap 2: job scrapers in batches van 5
    batches = [SCRAPERS[i:i + BATCH_SIZE] for i in range(0, len(SCRAPERS), BATCH_SIZE)]
    batch_task_groups = []

    for batch_idx, batch in enumerate(batches):
        with TaskGroup(group_id=f"batch_{batch_idx:02d}") as tg:
            for slug, module, klass in batch:
                PythonOperator(
                    task_id=f"scrape_{slug}",
                    python_callable=_make_scraper_callable(module, klass),
                    execution_timeout=timedelta(minutes=30),
                    # Fouten in één scraper mogen de rest van de batch niet stoppen
                    retries=1,
                    retry_delay=timedelta(minutes=3),
                )
        batch_task_groups.append(tg)

    # Stap 3: link-validatie
    validate_links = PythonOperator(
        task_id="validate_links",
        python_callable=run_link_validation,
        execution_timeout=timedelta(hours=2),  # kan lang duren bij veel URLs
    )

    # ── Afhankelijkheden: branches → batch_00 → batch_01 → … → validate ──────
    scrape_branches >> batch_task_groups[0]
    for i in range(len(batch_task_groups) - 1):
        batch_task_groups[i] >> batch_task_groups[i + 1]
    batch_task_groups[-1] >> validate_links
