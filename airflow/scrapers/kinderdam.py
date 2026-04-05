"""
Kinderdam scraper — ikwerkaandetoekomst.nl

Scraping structuur (3 niveaus):
  1. Hoofdpagina /vacatures-kinderopvang-en-kindontwikkeling
     → Banner toont 14 regio-subpagina's (a.webBanner-banneritem)
  2. Elke regio-pagina (bijv. /vacatures-kinderopvang-rotterdam-centrum)
     → Toont vacaturekaarten (a.vtlink[href*=vacaturebeschrijving])
     → Elke kaart bevat: titel, werksoort, standplaats, uren (span.text in volgorde)
  3. Detailpagina (/vacaturebeschrijving-kinderdam/[slug])
     → Volledige functiebeschrijving

Dubbele vacatures (zelfde URL op meerdere regio-pagina's) worden
gededupliceerd op source_url.

Site gebruikt Anta CMS (AFAS) met JavaScript-rendering. Playwright
is vereist om de pagina volledig te renderen.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ikwerkaandetoekomst.nl"
JOBS_URL = f"{BASE_URL}/vacatures-kinderopvang-en-kindontwikkeling"

# Banner-div ID op hoofdpagina (regio-links)
BANNER_CONTENT_ID = "P_C_W_DE4F98294C77056F1870AF8B77D269DD_Content"

# ── Regex parsers ──────────────────────────────────────────────────────────────
HOURS_RE    = re.compile(r"(\d+)\s*[-–]\s*(\d+)", re.I)
SALARY_RE   = re.compile(r"€\s*([\d.,]+)\s*[-–]\s*€?\s*([\d.,]+)", re.I)
AGE_RE      = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*jaar", re.I)
POSTCODE_RE = re.compile(r"(\d{4}\s*[A-Z]{2})")
STREET_RE   = re.compile(
    r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-\.]{3,50}?)\s+(\d{1,4}[a-zA-Z]{0,2})"
    r"(?=\s*[,\n]?\s*\d{4}\s*[A-Z]{2})",
    re.I,
)

CONTRACT_MAP = {
    "fulltime":  "fulltime",
    "full-time": "fulltime",
    "parttime":  "parttime",
    "part-time": "parttime",
    "tijdelijk": "temp",
}

# Werksoort → job_type (CAO functies)
WERKSOORT_MAP = {
    "bso":                     "bso_begeleider",
    "kdv":                     "pm3",
    "kdv/bso":                 "pm3",
    "peuteropvang":            "pm3",
    "gastouder":               "gastouder",
    "nanny":                   "nanny",
    "stagiair":                "stagiair",
    "teamleider":              "teamleider",
    "locatiemanager":          "locatiemanager",
    "coördinator":             "coordinator_bso",
    "pedagogisch professional": "senior_pm",
}


def _parse_euros(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def _parse_contract(raw: str) -> str:
    for key, val in CONTRACT_MAP.items():
        if key in raw.lower():
            return val
    return ""


def _werksoort_to_job_type(werksoort: str) -> str:
    ws = werksoort.lower().strip()
    for key, val in WERKSOORT_MAP.items():
        if key in ws:
            return val
    return ""


def _render_page(context: BrowserContext, url: str, wait_for_id: str | None = None) -> str:  # pragma: no cover
    """Render een pagina met Playwright en geef de volledige HTML terug."""
    page = context.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60_000)
        if wait_for_id:
            try:
                page.wait_for_function(
                    f"document.getElementById('{wait_for_id}')?.children?.length > 0",
                    timeout=30_000,
                )
            except PlaywrightTimeout:
                logger.warning(f"[kinderdam] Timeout wachten op #{wait_for_id}")
        page.wait_for_timeout(2_000)
        return page.content()
    finally:
        page.close()


def _get_regio_urls(html: str) -> list[str]:
    """
    Extraheer regio-subpagina URL's van de hoofdvacaturepagina.
    Verwacht: a.webBanner-banneritem met href naar regio-pagina's.
    """
    soup = BeautifulSoup(html, "lxml")
    banner = soup.find(id=BANNER_CONTENT_ID) or soup
    urls = []
    for a in banner.select("a.webBanner-banneritem[href]"):
        href = a.get("href", "")
        if not href.startswith("http"):
            href = BASE_URL + href
        if href and href not in urls:
            urls.append(href)
    logger.info(f"[kinderdam] {len(urls)} regio-pagina's gevonden")
    return urls


def _extract_cards_from_regio_page(html: str) -> list[dict]:
    """
    Extraheer vacaturekaarten van een regio-subpagina.
    Verwacht: a.vtlink[href*='vacaturebeschrijving'] met span.text in volgorde:
      [0] titel, [1] werksoort, [2] standplaats/locatie, [3] uren
    """
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    jobs = []

    for card in soup.select("a.vtlink[href*='vacaturebeschrijving']"):
        href = card.get("href", "")
        if not href.startswith("http"):
            href = BASE_URL + href
        if not href or href in seen:
            continue
        seen.add(href)

        # span.text elementen in volgorde: titel, werksoort, standplaats, uren
        spans = [s.get_text(strip=True) for s in card.select("span.text") if s.get_text(strip=True)]

        title       = spans[0] if len(spans) > 0 else ""
        werksoort   = spans[1] if len(spans) > 1 else ""
        location    = spans[2] if len(spans) > 2 else ""
        uren_raw    = spans[3] if len(spans) > 3 else ""

        if not title:
            continue

        hours_min = hours_max = None
        m = HOURS_RE.search(uren_raw)
        if m:
            hours_min, hours_max = int(m.group(1)), int(m.group(2))
        else:
            sg = re.search(r"\b(\d+)\s*uur\b", uren_raw, re.I)
            if sg:
                hours_min = hours_max = int(sg.group(1))

        jobs.append({
            "source_url":       href,
            "external_id":      href.rstrip("/").split("/")[-1],
            "title":            title,
            "short_description": "",
            "description":      "",
            "location_name":    location,
            "city":             "",
            "postcode":         "",
            "salary_min":       None,
            "salary_max":       None,
            "hours_min":        hours_min,
            "hours_max":        hours_max,
            "age_min":          None,
            "age_max":          None,
            "contract_type":    "",
            "job_type":         _werksoort_to_job_type(werksoort),
        })

    return jobs


def _extract_description_from_html(html: str) -> str:
    """Extraheer vacaturebeschrijving van een detailpagina."""
    soup = BeautifulSoup(html, "lxml")
    for sel in [
        "[class*='job-description']",
        "[class*='vacancy-description']",
        "[class*='freehtmlparagraph']",
        ".staticwebform",
        "article",
        "main",
    ]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text) > 50:
                return text[:5000]
    return ""


def _extract_address_from_html(html: str) -> tuple[str, str, str]:
    """
    Extraheer adres (postcode, stad, locatie_naam) van een detailpagina.
    Geeft (postcode, city, location_name) terug — leeg als niet gevonden.
    """
    if not html:
        return "", "", ""
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup.find("article") or soup
    text = main.get_text(separator=" ", strip=True)

    pc_m = POSTCODE_RE.search(text)
    if not pc_m:
        return "", "", ""

    postcode = pc_m.group(1).replace(" ", "")

    # City after postcode
    after = text[pc_m.end():pc_m.end() + 80]
    city_m = re.match(
        r"\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{1,40}?)(?:\s*[•·\n]|\s{2,}|\s+[A-Z][a-z]|\s*$)",
        after,
    )
    city = city_m.group(1).strip() if city_m else ""

    # Street + number before postcode
    before = text[max(0, pc_m.start() - 120):pc_m.start()]
    st_m = STREET_RE.search(before + " " + pc_m.group(1))
    if st_m:
        street = f"{st_m.group(1).strip()} {st_m.group(2).strip()}"
        location_name = f"{street}, {postcode} {city}".strip(", ").strip()
    elif city:
        location_name = f"{postcode} {city}"
    else:
        location_name = postcode

    return postcode, city, location_name


class KinderdamScraper(BaseScraper):
    company_slug = "kinderdam"

    def fetch_company(self) -> dict:
        """Scrapet bedrijfsinfo van de homepage."""
        try:
            resp = requests.get(BASE_URL, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            logo_url = ""
            for sel in ["header img[src]", ".logo img[src]", "img.logo[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    logo_url = src if src.startswith("http") else BASE_URL + src
                    break

            description = ""
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")

        except Exception as exc:
            logger.warning(f"[kinderdam] Bedrijfsinfo ophalen mislukt: {exc}")
            logo_url = ""
            description = ""

        return {
            "name": "Kinderdam",
            "website": BASE_URL,
            "job_board_url": JOBS_URL,
            "scraper_class": "KinderdamScraper",
            "logo_url": logo_url,
            "description": description,
        }

    def fetch_jobs(self) -> list[dict]:
        logger.info(f"[kinderdam] Start scrape via Playwright: {JOBS_URL}")

        with sync_playwright() as pw:  # pragma: no cover
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=SCRAPER_HEADERS["User-Agent"],
                locale="nl-NL",
            )

            try:
                # Niveau 1: hoofdpagina → regio-links
                html_main = _render_page(context, JOBS_URL, wait_for_id=BANNER_CONTENT_ID)
                regio_urls = _get_regio_urls(html_main)

                if not regio_urls:
                    logger.warning("[kinderdam] Geen regio-pagina's gevonden")
                    return []

                # Niveau 2: elke regio-pagina → vacaturekaarten
                all_jobs: dict[str, dict] = {}  # source_url → job dict (deduplicatie)
                for regio_url in regio_urls:
                    logger.info(f"[kinderdam] Regio: {regio_url}")
                    try:
                        html_regio = _render_page(context, regio_url)
                        cards = _extract_cards_from_regio_page(html_regio)
                        for job in cards:
                            if job["source_url"] not in all_jobs:
                                all_jobs[job["source_url"]] = job
                    except Exception as exc:
                        logger.warning(f"[kinderdam] Regio-pagina mislukt {regio_url}: {exc}")
                    time.sleep(0.5)

                jobs = list(all_jobs.values())
                logger.info(f"[kinderdam] Totaal unieke vacatures: {len(jobs)}")

                if not jobs:
                    return []

                # Niveau 3: detailpagina's → beschrijvingen + adres
                logger.info(f"[kinderdam] Detail scraping voor {len(jobs)} vacatures...")
                for job in jobs:
                    try:
                        detail_html = _render_page(context, job["source_url"])
                        job["description"] = _extract_description_from_html(detail_html)
                        postcode, city, location_name = _extract_address_from_html(detail_html)
                        if location_name:
                            job["location_name"] = location_name
                        if postcode:
                            job["postcode"] = postcode
                        if city and not job.get("city"):
                            job["city"] = city
                        time.sleep(0.5)
                    except Exception as exc:
                        logger.warning(f"[kinderdam] Detail mislukt {job['source_url']}: {exc}")

            finally:
                context.close()
                browser.close()

        return jobs
