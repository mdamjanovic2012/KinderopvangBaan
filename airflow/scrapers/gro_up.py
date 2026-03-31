"""
Gro-up kinderopvang scraper — werkenbijgro-up.nl

Platform: Nuxt SSR custom site (geen Teamtailor/RSS)

Aanpak:
  1. Haal sitemap.xml op — bevat alle job-URLs als root-level slugs
  2. Filter op kinderopvang-trefwoorden (sluit kraamzorg/jeugdhulp/buurtwerk uit)
  3. Scrape elke detailpagina voor titel, uren, salaris, locatie, beschrijving

Job-URL patroon: https://www.werkenbijgro-up.nl/{job-slug}
Kinderopvang vacatures bevatten in slug: pedagogisch, bso, kdv, peuteropvang,
activiteitenbegeleider, adjunct-locatiemanager, senior-locatiemanager, regiomanager,
locatiemanager, pedagogisch-coach, bijbaan, zij-instroom, bbl
"""

import logging
import re
import time
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL    = "https://www.werkenbijgro-up.nl"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
JOBS_URL    = f"{BASE_URL}/kinderopvang/vacatures/"

HOURS_RE   = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*uur", re.I)
SALARY_RE  = re.compile(r"€\s*([\d.,]+)\s*(?:tot|[-–])\s*€?\s*([\d.,]+)", re.I)
CITY_RE    = re.compile(r"\d{4}\s*[A-Z]{2}\s+([A-Za-zÀ-ÿ\s\-]+?)(?:\s*•|\s*$)", re.I)
POSTCODE_RE = re.compile(r"(\d{4}\s*[A-Z]{2})")

# Trefwoorden die een URL identificeren als kinderopvang
KO_KEYWORDS = (
    "pedagogisch", "bso", "kdv", "peuteropvang", "activiteitenbegeleider",
    "locatiemanager", "pedagogisch-coach", "bijbaan", "zij-instroom", "bbl",
    "flexpool", "groepsleider", "kinderopvang",
)

# Trefwoorden die een URL uitsluiten (andere afdelingen)
EXCLUDE_KEYWORDS = (
    "kraamverzorgende", "kraamzorg", "partusassistent", "verloskundige",
    "jongerenwerker", "jeugdhulp", "buurtverbinder", "buurtwerk",
    "zorgconsulent", "huis-van-de-wijk", "clientenraad",
)


def _parse_euros(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def get_ko_job_urls(sitemap_text: str) -> list[str]:
    """
    Parseer sitemap.xml en filter kinderopvang vacature-URL's.
    Kinderopvang jobs staan als root-level slugs: /pedagogisch-medewerker-kdv-...
    """
    try:
        root = ET.fromstring(sitemap_text)
    except ET.ParseError:
        return []

    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    urls = []
    for el in root.findall(f"{ns}url"):
        loc = (el.findtext(f"{ns}loc") or "").strip()
        if not loc:
            continue

        # Alleen root-level slugs (één segment na domein)
        path = loc.replace(BASE_URL, "").strip("/")
        if "/" in path or not path:
            continue

        slug = path.lower()

        # Sluit niet-kinderopvang uit
        if any(kw in slug for kw in EXCLUDE_KEYWORDS):
            continue

        # Accepteer alleen als er een kinderopvang-trefwoord in zit
        if any(kw in slug for kw in KO_KEYWORDS):
            urls.append(loc)

    return urls


def scrape_job_page(url: str) -> dict | None:
    """
    Scrape een Gro-up job detailpagina.
    Geeft dict of None bij mislukte scrape.
    """
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"[gro-up] Detailpagina mislukt {url}: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # Titel
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    if not title:
        return None

    # Hoofdinhoud
    main = soup.select_one("main") or soup.select_one("article") or soup.body
    text = main.get_text(separator=" ", strip=True) if main else ""

    # Uren
    hours_min = hours_max = None
    m = HOURS_RE.search(text)
    if m:
        hours_min, hours_max = int(m.group(1)), int(m.group(2))

    # Salaris
    salary_min = salary_max = None
    sm = SALARY_RE.search(text)
    if sm:
        salary_min = _parse_euros(sm.group(1))
        salary_max = _parse_euros(sm.group(2))

    # Postcode + stad
    city = postcode = ""
    pc_m = POSTCODE_RE.search(text)
    if pc_m:
        postcode = pc_m.group(1).replace(" ", "")
        # Zoek stad na postcode
        after = text[pc_m.end():pc_m.end() + 80]
        # Stad staat direct na de postcode, eindigt bij bullet, newline of nieuw zin (hfLetter + kleine)
        city_m = re.match(
            r"\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{1,40}?)(?:\s*[•·\n]|\s{2,}|\s+[A-Z][a-z]|\s*$)",
            after,
        )
        if city_m:
            city = city_m.group(1).strip()

    # Beschrijving (eerste 5000 tekens van main)
    desc = text[:5000] if text else ""

    external_id = url.rstrip("/").split("/")[-1]

    return {
        "source_url":        url,
        "external_id":       external_id,
        "title":             title,
        "short_description": desc[:300],
        "description":       desc,
        "location_name":     city or "",
        "city":              city,
        "postcode":          postcode,
        "salary_min":        salary_min,
        "salary_max":        salary_max,
        "hours_min":         hours_min,
        "hours_max":         hours_max,
        "age_min":           None,
        "age_max":           None,
        "contract_type":     "",
        "job_type":          "",
    }


class GroUpScraper(BaseScraper):
    company_slug = "gro-up"

    def fetch_company(self) -> dict:
        logo_url = description = ""
        try:
            resp = requests.get(BASE_URL, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for sel in ["header img[src]", ".logo img[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    logo_url = src if src.startswith("http") else BASE_URL + src
                    break
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")
        except Exception as exc:
            logger.warning(f"[gro-up] Bedrijfsinfo ophalen mislukt: {exc}")
        return {
            "name":          "Gro-up kinderopvang",
            "website":       BASE_URL,
            "job_board_url": JOBS_URL,
            "scraper_class": "GroUpScraper",
            "logo_url":      logo_url,
            "description":   description,
        }

    def fetch_jobs(self) -> list[dict]:
        logger.info(f"[gro-up] Sitemap ophalen: {SITEMAP_URL}")
        try:
            resp = requests.get(SITEMAP_URL, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"[gro-up] Sitemap ophalen mislukt: {exc}")
            return []

        urls = get_ko_job_urls(resp.text)
        logger.info(f"[gro-up] {len(urls)} kinderopvang vacature-URLs gevonden")

        jobs = []
        for url in urls:
            job = scrape_job_page(url)
            if job:
                jobs.append(job)
            time.sleep(0.3)

        logger.info(f"[gro-up] {len(jobs)} vacatures gescraped")
        return jobs
