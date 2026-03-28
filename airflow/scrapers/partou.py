"""
Partou scraper — werkenbijpartou.nl

Job board: https://www.werkenbijpartou.nl/vacatures

Partou gebruikt een API-achtige JSON endpoint voor vacatures.
Controleer via browser DevTools (Network tab) of er een /api/vacatures endpoint is.
Als dat niet beschikbaar is, val terug op HTML scraping.

SELECTOR AANPASSEN: als de site update, controleer de selectors via browser DevTools.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.werkenbijpartou.nl"
JOBS_URL = f"{BASE_URL}/vacatures"

# Probeer eerst een JSON API (veel moderne job boards hebben dit)
JSON_API_URL = f"{BASE_URL}/api/vacancies"  # aanpassen als anders

# ── CSS-selectors (aanpassen als de site wijzigt) ─────────────────────────────
CARD_SELECTOR  = "article.job, div.job-card, li.vacancy, .vacancy-item"
TITLE_SEL      = "h2, h3, .job-title, .vacancy-title"
URL_SEL        = "a[href]"
LOCATION_SEL   = ".location, [class*='location'], [class*='vestiging']"
CONTRACT_SEL   = ".contract, [class*='contract'], [class*='dienstverband']"
HOURS_SEL      = ".hours, [class*='hours'], [class*='uren']"
SALARY_SEL     = ".salary, [class*='salary'], [class*='salaris']"
AGE_SEL        = "[class*='age'], [class*='leeftijd'], [class*='groep']"
SHORT_DESC_SEL = ".excerpt, .intro, p.summary"
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


def _try_json_api(session: requests.Session) -> list[dict] | None:
    """
    Probeer een JSON API endpoint. Veel moderne job boards bieden dit aan.
    Geeft lijst van job dicts terug, of None als het niet werkt.
    """
    try:
        resp = session.get(JSON_API_URL, timeout=10)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
            data = resp.json()
            # Pas aan op de JSON structuur van Partou
            items = data if isinstance(data, list) else data.get("vacancies", data.get("results", []))
            if items:
                logger.info(f"[partou] JSON API beschikbaar: {len(items)} items")
                return _parse_json_items(items)
    except Exception:
        pass
    return None


def _parse_json_items(items: list) -> list[dict]:
    """Pas aan op de JSON structuur van Partou's API."""
    jobs = []
    for item in items:
        url = item.get("url") or item.get("link") or item.get("applyUrl", "")
        if not url or not url.startswith("http"):
            url = BASE_URL + url if url else ""
        if not url:
            continue

        title = item.get("title") or item.get("name", "")
        location = item.get("location") or item.get("city") or item.get("vestiging", "")
        hours_text = str(item.get("hours") or item.get("uren", ""))
        salary_text = str(item.get("salary") or item.get("salaris", ""))

        hours_min = hours_max = None
        m = HOURS_RE.search(hours_text)
        if m:
            hours_min, hours_max = int(m.group(1)), int(m.group(2))

        salary_min = salary_max = None
        m = SALARY_RE.search(salary_text)
        if m:
            salary_min = _parse_euros(m.group(1))
            salary_max = _parse_euros(m.group(2))

        jobs.append({
            "source_url": url,
            "external_id": str(item.get("id", "")),
            "title": title,
            "short_description": item.get("summary") or item.get("intro", ""),
            "description": item.get("description", ""),
            "location_name": location,
            "hours_min": hours_min,
            "hours_max": hours_max,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "age_min": None,
            "age_max": None,
            "contract_type": _parse_contract(str(item.get("contractType", ""))),
            "job_type": "",
        })
    return jobs


def _scrape_html(session: requests.Session) -> list[dict]:
    """HTML scraping als fallback."""
    jobs = []
    page = 1

    while True:
        url = JOBS_URL if page == 1 else f"{JOBS_URL}?page={page}"
        logger.info(f"[partou] Pagina {page}: {url}")

        try:
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"[partou] Ophalen mislukt: {exc}")
            break

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select(CARD_SELECTOR)

        if not cards:
            break

        for card in cards:
            link = card.select_one(URL_SEL)
            if not link:
                continue
            href = link.get("href", "")
            if not href.startswith("http"):
                href = BASE_URL + href

            title_el = card.select_one(TITLE_SEL)
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
            if not title:
                continue

            loc_el = card.select_one(LOCATION_SEL)
            location_name = loc_el.get_text(strip=True) if loc_el else ""

            hours_el = card.select_one(HOURS_SEL)
            hours_text = hours_el.get_text(strip=True) if hours_el else ""
            hours_min = hours_max = None
            m = HOURS_RE.search(hours_text)
            if m:
                hours_min, hours_max = int(m.group(1)), int(m.group(2))

            salary_el = card.select_one(SALARY_SEL)
            salary_text = salary_el.get_text(strip=True) if salary_el else ""
            salary_min = salary_max = None
            m = SALARY_RE.search(salary_text)
            if m:
                salary_min = _parse_euros(m.group(1))
                salary_max = _parse_euros(m.group(2))

            age_el = card.select_one(AGE_SEL)
            age_text = age_el.get_text(strip=True) if age_el else title
            age_min = age_max = None
            m = AGE_RE.search(age_text)
            if m:
                age_min, age_max = int(m.group(1)), int(m.group(2))

            contract_el = card.select_one(CONTRACT_SEL)
            contract_raw = contract_el.get_text(strip=True) if contract_el else ""

            short_el = card.select_one(SHORT_DESC_SEL)
            short_desc = short_el.get_text(strip=True) if short_el else ""

            jobs.append({
                "source_url": href,
                "external_id": href.rstrip("/").split("/")[-1],
                "title": title,
                "short_description": short_desc,
                "description": "",
                "location_name": location_name,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "hours_min": hours_min,
                "hours_max": hours_max,
                "age_min": age_min,
                "age_max": age_max,
                "contract_type": _parse_contract(contract_raw),
                "job_type": "",
            })

        next_btn = soup.select_one("a[rel='next'], .pagination .next, a.next-page")
        if not next_btn:
            break
        page += 1
        time.sleep(1)

    return jobs


class PartouScraper(BaseScraper):
    company_slug = "partou"

    def fetch_company(self) -> dict:
        """Scrapet bedrijfsinfo van de Partou homepage."""
        partou_home = "https://www.partou.nl"
        try:
            resp = requests.get(partou_home, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            logo_url = ""
            for sel in ["header img[src]", ".logo img[src]", "img.logo[src]", "img[alt*='partou' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    logo_url = src if src.startswith("http") else partou_home + src
                    break

            description = ""
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")

        except Exception as exc:
            logger.warning(f"[partou] Bedrijfsinfo ophalen mislukt: {exc}")
            logo_url = ""
            description = ""

        return {
            "name": "Partou",
            "website": partou_home,
            "job_board_url": JOBS_URL,
            "scraper_class": "PartouScraper",
            "logo_url": logo_url,
            "description": description,
        }

    def fetch_jobs(self) -> list[dict]:
        session = requests.Session()
        session.headers.update(SCRAPER_HEADERS)

        # Probeer eerst JSON API, anders HTML
        jobs = _try_json_api(session)
        if jobs is None:
            logger.info("[partou] JSON API niet beschikbaar, gebruik HTML scraping")
            jobs = _scrape_html(session)

        return jobs
