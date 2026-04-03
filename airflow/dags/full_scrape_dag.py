"""
DAG: full_scrape
Volledige scrape-pipeline, 3× per week 's nachts (ma/wo/vr om 02:00).

Stappen:
  1. scrape_branches     — bijwerk vestigingen-adressen (PDOK geocoding)
  2. scrape_jobs_batch_* — alle scrapers in batches van 5 (parallel per batch,
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
    # ── Bestaande scrapers ────────────────────────────────────────────────────
    ("bijdehandjes",    "scrapers.bijdehandjes",        "BijdeHandjesScraper"),
    ("bink",            "scrapers.bink",                "BinkScraper"),
    ("compananny",      "scrapers.compananny",          "CompaNannyScraper"),
    ("dak",             "scrapers.dak",                 "DakScraper"),
    ("dichtbij",        "scrapers.dichtbij",            "DichtbijScraper"),
    ("doomijn",         "scrapers.doomijn",             "DoomijnScraper"),
    ("gro_up",          "scrapers.gro_up",              "GroUpScraper"),
    ("humankind",       "scrapers.humankind",           "HumankindScraper"),
    ("kanteel",         "scrapers.kanteel",             "KanteelScraper"),
    ("kibeo",           "scrapers.kibeo",               "KibeoScraper"),
    ("kids_first",      "scrapers.kids_first",          "KidsFirstScraper"),
    ("kinderdam",       "scrapers.kinderdam",           "KinderdamScraper"),
    ("kindergarden",    "scrapers.kindergarden",        "KindergardenScraper"),
    ("kinderwoud",      "scrapers.kinderwoud",          "KinderwoudScraper"),
    ("kion",            "scrapers.kion",                "KIONScraper"),
    ("ko_walcheren",    "scrapers.ko_walcheren",        "KOWalcherenScraper"),
    ("kober",           "scrapers.kober",               "KoberScraper"),
    ("mik",             "scrapers.mik",                 "MIKScraper"),
    ("norlandia",       "scrapers.norlandia",           "NorlandiaScraper"),
    ("op_stoom",        "scrapers.op_stoom",            "OpStoomScraper"),
    ("partou",          "scrapers.partou",              "PartouScraper"),
    ("prokino",         "scrapers.prokino",             "ProkinoScraper"),
    ("samenwerkende_ko","scrapers.samenwerkende_ko",    "SamenwerkendeKOScraper"),
    ("sinne",           "scrapers.sinne",               "SinneScraper"),
    ("ska",             "scrapers.ska",                 "SkaScraper"),
    ("spring",          "scrapers.spring_kinderopvang", "SpringKinderopvangScraper"),
    ("tinteltuin",      "scrapers.tinteltuin",          "TintelTuinScraper"),
    ("twee_samen",      "scrapers.twee_samen",          "TweeSamenScraper"),
    ("wasko",           "scrapers.wasko",               "WaskoScraper"),
    ("wij_zijn_jong",   "scrapers.wij_zijn_jong",       "WijZijnJONGScraper"),
    # ── Nieuwe scrapers (WordPress) ───────────────────────────────────────────
    ("avonturijn",      "scrapers.avonturijn",          "AvonturijnScraper"),
    ("bzzzonder",       "scrapers.bzzzonder",           "BzzzonderScraper"),
    ("de_eerste_stap",  "scrapers.de_eerste_stap",      "DeEersteStapScraper"),
    ("de_lange_keizer", "scrapers.de_lange_keizer",     "DeLangeKeizerScraper"),
    ("flekss",          "scrapers.flekss",              "FlekssScraper"),
    ("floreokids",      "scrapers.floreokids",          "FloreoKidsScraper"),
    ("forte",           "scrapers.forte",               "ForteScraper"),
    ("gmk",             "scrapers.gmk",                 "GmkScraper"),
    ("go_kinderopvang", "scrapers.go_kinderopvang",     "GoKinderopvangScraper"),
    ("goo",             "scrapers.goo",                 "GooScraper"),
    ("hero",            "scrapers.hero",                "HeroScraper"),
    ("hoera",           "scrapers.hoera",               "HoeraScraper"),
    ("junis",           "scrapers.junis",               "JunisScraper"),
    ("kiddoozz",        "scrapers.kiddoozz",            "KiddoozzScraper"),
    ("kids2b",          "scrapers.kids2b",              "Kids2bScraper"),
    ("kidscasa",        "scrapers.kidscasa",            "KidscasaScraper"),
    ("kindernet",       "scrapers.kindernet",           "KindernetScraper"),
    ("kinderrijk",      "scrapers.kinderrijk",          "KinderrijkScraper"),
    ("kindertuin",      "scrapers.kindertuin",          "KindertuinScraper"),
    ("klein_alkmaar",   "scrapers.klein_alkmaar",       "KleinAlkmaarScraper"),
    ("kleurrijk",       "scrapers.kleurrijk",           "KleurrijkScraper"),
    ("ko_friesland",    "scrapers.ko_friesland",        "KoFrieslandScraper"),
    ("ko_purmerend",    "scrapers.ko_purmerend",        "KoPurmerendScraper"),
    ("komkids",         "scrapers.komkids",             "KomKidsScraper"),
    ("koos",            "scrapers.koos",                "KoosScraper"),
    ("kosmo",           "scrapers.kosmo",               "KosmoScraper"),
    ("ksh",             "scrapers.ksh",                 "KshScraper"),
    ("lps",             "scrapers.lps",                 "LpsScraper"),
    ("monter",          "scrapers.monter",              "MonterScraper"),
    ("morgen",          "scrapers.morgen",              "MorgenScraper"),
    ("nummereen",       "scrapers.nummereen",           "NummereenScraper"),
    ("okidoki",         "scrapers.okidoki",             "OkidokiScraper"),
    ("puckco",          "scrapers.puckco",              "PuckcoScraper"),
    ("quadrant",        "scrapers.quadrant",            "QuadrantScraper"),
    ("riant",           "scrapers.riant",               "RiantScraper"),
    ("scio",            "scrapers.scio",                "ScioScraper"),
    ("sdk",             "scrapers.sdk",                 "SdkScraper"),
    ("skbnm",           "scrapers.skbnm",               "SkbnmScraper"),
    ("skdd",            "scrapers.skdd",                "SkddScraper"),
    ("skid",            "scrapers.skid",                "SkidScraper"),
    ("solidoe",         "scrapers.solidoe",             "SolidoeScraper"),
    ("unikidz",         "scrapers.unikidz",             "UniKidzScraper"),
    ("vlietkinderen",   "scrapers.vlietkinderen",       "VlietkinderenScraper"),
    ("welluswijs",      "scrapers.welluswijs",          "WelluswijsScraper"),
    ("wildewijs",       "scrapers.wildewijs",           "WildewijsScraper"),
    ("woest_zuid",      "scrapers.woest_zuid",          "WoestZuidScraper"),
    ("xpect013",        "scrapers.xpect013",            "Xpect013Scraper"),
    # ── Nieuwe scrapers (Teamtailor RSS) ──────────────────────────────────────
    ("monkey_donky",    "scrapers.monkey_donky",        "MonkeyDonkyScraper"),
    # ── Nieuwe scrapers (Recruitee API) ───────────────────────────────────────
    ("rastergroep",     "scrapers.rastergroep",         "RastergroepScraper"),
    # ── Nieuwe scrapers (custom platforms) ───────────────────────────────────
    ("atalenta",        "scrapers.atalenta",            "AtalentaScraper"),
    ("avem",            "scrapers.avem",                "AvemScraper"),
    ("basker",          "scrapers.basker",              "BaskerScraper"),
    ("berend_botje",    "scrapers.berend_botje",        "BerendBotjeScraper"),
    ("blosse",          "scrapers.blosse",              "BlosseScraper"),
    ("ckc_drenthe",     "scrapers.ckc_drenthe",         "CKCDrentheScraper"),
    ("haarlemmermeer",  "scrapers.haarlemmermeer",      "HaarlemmermeerScraper"),
    ("kindencoludens",  "scrapers.kindencoludens",      "KindenCoLudensScraper"),
    ("kinderopvang_roermond", "scrapers.kinderopvang_roermond", "KinderopvangRoermondScraper"),
    ("kinderstad",      "scrapers.kinderstad",          "KinderstadScraper"),
    ("mikz",            "scrapers.mikz",                "MikzScraper"),
    ("skippypepijn",    "scrapers.skippypepijn",        "SkippyPePijNScraper"),
    ("sportstuif",      "scrapers.sportstuif",          "SportstuifScraper"),
    ("t_nest",          "scrapers.t_nest",              "TNestScraper"),
    ("un1ek",           "scrapers.un1ek",               "Un1ekScraper"),
    ("yes_kinderopvang","scrapers.yes_kinderopvang",    "YesKinderopvangScraper"),
]

BATCH_SIZE = 5


def _make_scraper_callable(module: str, klass: str):
    """Geeft een callable terug die de scraper importeert en uitvoert.

    Fouten worden gelogd maar niet opnieuw gegooid zodat één falende scraper
    de rest van de batch niet blokkeert. scrape_branches mag wél falen en
    stopt dan de hele pipeline via de standaard ALL_SUCCESS trigger-regel.
    """
    def run():
        import importlib
        try:
            mod = importlib.import_module(module)
            scraper_cls = getattr(mod, klass)
            stats = scraper_cls().run()
            print(f"[{klass}] resultaat: {stats}")
            return stats
        except Exception as exc:
            print(f"[{klass}] FOUT (overgeslagen): {exc}")
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
        execution_timeout=timedelta(hours=2),
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
                    retries=1,
                    retry_delay=timedelta(minutes=3),
                )
        batch_task_groups.append(tg)

    # Stap 3: link-validatie
    validate_links = PythonOperator(
        task_id="validate_links",
        python_callable=run_link_validation,
        execution_timeout=timedelta(hours=2),
    )

    # ── Afhankelijkheden: branches → batch_00 → batch_01 → … → validate ──────
    scrape_branches >> batch_task_groups[0]
    for i in range(len(batch_task_groups) - 1):
        batch_task_groups[i] >> batch_task_groups[i + 1]
    batch_task_groups[-1] >> validate_links
