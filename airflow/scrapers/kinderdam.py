"""
Kinderdam scraper — ikwerkaandetoekomst.nl

Job board: https://www.ikwerkaandetoekomst.nl/vacatures-kinderopvang-en-kindontwikkeling

Aanpak:
- Laad de vacaturepagina met BeautifulSoup
- Haal alle vacaturekaarten op (klasse .vacancy-card of vergelijkbaar)
- Bezoek elke detailpagina voor beschrijving + extra metadata

SELECTOR AANPASSEN: als de site update, zoek eerst de correcte selectors via
'Inspecteren' in de browser. Verander CARD_SELECTOR, TITLE_SEL, etc.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ikwerkaandetoekomst.nl"
JOBS_URL = f"{BASE_URL}/vacatures-kinderopvang-en-kindontwikkeling"

# ── CSS-selectors (aanpassen als de site wijzigt) ─────────────────────────────
CARD_SELECTOR      = "article.vacancy, div.vacancy-item, li.job-listing"
TITLE_SEL          = "h2, h3, .vacancy-title, .job-title"
URL_SEL            = "a[href]"
LOCATION_SEL       = ".location, .vacancy-location, [class*='location']"
CONTRACT_SEL       = ".contract-type, [class*='contract'], [class*='dienstverband']"
HOURS_SEL          = ".hours, [class*='hours'], [class*='uren']"
SALARY_SEL         = ".salary, [class*='salary'], [class*='salaris']"
AGE_SEL            = ".age-group, [class*='age'], [class*='leeftijd']"
SHORT_DESC_SEL     = ".excerpt, .summary, p.description"
# ─────────────────────────────────────────────────────────────────────────────

HOURS_RE   = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*uur", re.I)
SALARY_RE  = re.compile(r"€\s*([\d.,]+)\s*[-–]\s*€?\s*([\d.,]+)", re.I)
AGE_RE     = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*jaar", re.I)

CONTRACT_MAP = {
    "fulltime": "fulltime",
    "full-time": "fulltime",
    "parttime": "parttime",
    "part-time": "parttime",
    "tijdelijk": "temp",
    "temporary": "temp",
}


def _parse_euros(raw: str) -> float | None:
    cleaned = raw.replace(".", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_contract(raw: str) -> str:
    for key, val in CONTRACT_MAP.items():
        if key in raw.lower():
            return val
    return ""


def _scrape_detail(url: str, session: requests.Session) -> dict:
    """Haal detailpagina op en extraheer extra velden."""
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        description = ""
        for sel in [".job-description", ".vacancy-description", "article .content", "main"]:
            el = soup.select_one(sel)
            if el:
                description = el.get_text(separator="\n", strip=True)
                break

        return {"description": description}
    except Exception as exc:
        logger.warning(f"Detailpagina mislukt voor {url}: {exc}")
        return {}


class KinderdamScraper(BaseScraper):
    company_slug = "kinderdam"

    def fetch_company(self) -> dict:
        """Scrapet bedrijfsinfo van de Kinderdam homepage."""
        try:
            resp = requests.get(BASE_URL, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            # Logo — zoek in header
            logo_url = ""
            for sel in ["header img[src]", ".logo img[src]", "img.logo[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    logo_url = src if src.startswith("http") else BASE_URL + src
                    break

            # Beschrijving — meta description of eerste alinea
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
        session = requests.Session()
        session.headers.update(SCRAPER_HEADERS)

        jobs = []
        page = 1

        while True:
            url = JOBS_URL if page == 1 else f"{JOBS_URL}?page={page}"
            logger.info(f"[kinderdam] Pagina {page}: {url}")

            try:
                resp = session.get(url, timeout=20)
                resp.raise_for_status()
            except Exception as exc:
                logger.error(f"[kinderdam] Ophalen mislukt: {exc}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select(CARD_SELECTOR)

            if not cards:
                logger.info(f"[kinderdam] Geen kaarten op pagina {page}, stop.")
                break

            for card in cards:
                # URL + externe ID
                link = card.select_one(URL_SEL)
                if not link:
                    continue
                href = link.get("href", "")
                if not href.startswith("http"):
                    href = BASE_URL + href
                external_id = href.rstrip("/").split("/")[-1]

                # Titel
                title_el = card.select_one(TITLE_SEL)
                title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
                if not title:
                    continue

                # Locatie
                loc_el = card.select_one(LOCATION_SEL)
                location_name = loc_el.get_text(strip=True) if loc_el else ""

                # Contract
                contract_el = card.select_one(CONTRACT_SEL)
                contract_raw = contract_el.get_text(strip=True) if contract_el else ""
                contract_type = _parse_contract(contract_raw)

                # Uren
                hours_el = card.select_one(HOURS_SEL)
                hours_text = hours_el.get_text(strip=True) if hours_el else ""
                hours_min = hours_max = None
                m = HOURS_RE.search(hours_text)
                if m:
                    hours_min, hours_max = int(m.group(1)), int(m.group(2))

                # Salaris
                salary_el = card.select_one(SALARY_SEL)
                salary_text = salary_el.get_text(strip=True) if salary_el else ""
                salary_min = salary_max = None
                m = SALARY_RE.search(salary_text)
                if m:
                    salary_min = _parse_euros(m.group(1))
                    salary_max = _parse_euros(m.group(2))

                # Leeftijdsgroep
                age_el = card.select_one(AGE_SEL)
                age_text = age_el.get_text(strip=True) if age_el else title
                age_min = age_max = None
                m = AGE_RE.search(age_text)
                if m:
                    age_min, age_max = int(m.group(1)), int(m.group(2))

                # Korte beschrijving
                short_el = card.select_one(SHORT_DESC_SEL)
                short_desc = short_el.get_text(strip=True) if short_el else ""

                jobs.append({
                    "source_url": href,
                    "external_id": external_id,
                    "title": title,
                    "short_description": short_desc,
                    "description": "",        # ingevuld via detail scrape
                    "location_name": location_name,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "hours_min": hours_min,
                    "hours_max": hours_max,
                    "age_min": age_min,
                    "age_max": age_max,
                    "contract_type": contract_type,
                    "job_type": "",
                })

            # Controleer of er een volgende pagina is
            next_btn = soup.select_one("a[rel='next'], .pagination .next, a.next-page")
            if not next_btn:
                break
            page += 1
            time.sleep(1)  # beleefd wachten

        # Haal beschrijvingen op via detailpagina's (max 5 gelijktijdig, beleefd)
        logger.info(f"[kinderdam] Detail scraping voor {len(jobs)} vacatures...")
        for job in jobs:
            detail = _scrape_detail(job["source_url"], session)
            job.update(detail)
            time.sleep(0.5)

        return jobs
