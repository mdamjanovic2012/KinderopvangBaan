"""
Spring Kinderopvang scraper — werkenbijspring.nl

Platform: Custom PHP CMS (niet Teamtailor)

Aanpak:
  1. Haal vacaturelijst op van /nl/vacatures (HTML)
     Job-URLs zijn ingebed als: window.location = '/nl/vacatures/{id}-{slug}'
  2. Scrape elke detailpagina voor titel, uren, stad en beschrijving

Detail-pagina structuur (pipe-separated tekst):
  {Contracttype} | {X uur} | {Stad}
  Uren: "18 uur", "24 - 32 uur" etc.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL  = "https://www.werkenbijspring.nl"
JOBS_URL  = f"{BASE_URL}/nl/vacatures"

HOURS_RE    = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*uur", re.I)
HOURS_1_RE  = re.compile(r"\b(\d+)\s*uur\b", re.I)
SALARY_RE   = re.compile(r"€\s*([\d.,]+)\s*(?:tot|[-–])\s*€?\s*([\d.,]+)", re.I)

CONTRACT_MAP = {
    "vaste uren":      "fulltime",
    "fulltime":        "fulltime",
    "part-time":       "parttime",
    "parttime":        "parttime",
    "tijdelijk":       "temp",
    "oproepkracht":    "temp",
    "bijbaan":         "parttime",
}


def _parse_euros(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def get_spring_job_urls(html: str) -> list[str]:
    """
    Extraheer vacature-URLs uit de listingpagina.
    URL patroon: window.location = '/nl/vacatures/{id}-{slug}';
    """
    slugs = re.findall(r"window\.location\s*=\s*'(/nl/vacatures/[^']+)'", html)
    seen = set()
    urls = []
    for slug in slugs:
        url = BASE_URL + slug
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def scrape_spring_job_page(url: str) -> dict | None:
    """Scrape een Spring vacature detailpagina."""
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"[spring] Detailpagina mislukt {url}: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    if not title:
        return None

    text = soup.body.get_text(separator=" | ", strip=True) if soup.body else ""

    # Uren — formaat "24 - 32 uur" of "18 uur"
    hours_min = hours_max = None
    m = HOURS_RE.search(text)
    if m:
        hours_min, hours_max = int(m.group(1)), int(m.group(2))
    else:
        m1 = HOURS_1_RE.search(text)
        if m1:
            hours_min = hours_max = int(m1.group(1))

    # Contract type
    contract_type = ""
    text_lower = text.lower()
    for key, val in CONTRACT_MAP.items():
        if key in text_lower:
            contract_type = val
            break

    # Stad — staat na het uren-block in de pipe-separated tekst
    city = ""
    # Zoek patroon: "| X uur | {stad} |"
    city_m = re.search(r"\|\s*\d+(?:\s*[-–]\s*\d+)?\s*uur\s*\|\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-']{1,40}?)\s*\|", text, re.I)
    if city_m:
        city = city_m.group(1).strip()

    # Salaris
    salary_min = salary_max = None
    sm = SALARY_RE.search(text)
    if sm:
        salary_min = _parse_euros(sm.group(1))
        salary_max = _parse_euros(sm.group(2))

    # Beschrijving
    desc = ""
    for sel in ["[class*='vacature-content']", "[class*='job-description']", "article", "main .content", ".page-content-inner"]:
        el = soup.select_one(sel)
        if el:
            t = el.get_text(separator="\n", strip=True)
            if len(t) > 100:
                desc = t[:5000]
                break

    external_id = url.rstrip("/").split("/")[-1]

    return {
        "source_url":        url,
        "external_id":       external_id,
        "title":             title,
        "short_description": desc[:300],
        "description":       desc,
        "location_name":     city,
        "city":              city,
        "salary_min":        salary_min,
        "salary_max":        salary_max,
        "hours_min":         hours_min,
        "hours_max":         hours_max,
        "age_min":           None,
        "age_max":           None,
        "contract_type":     contract_type,
        "job_type":          "",
    }


class SpringKinderopvangScraper(BaseScraper):
    company_slug = "spring"

    def fetch_company(self) -> dict:
        logo_url = description = ""
        try:
            resp = requests.get(BASE_URL, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for sel in ["header img[src]", ".logo img[src]", "img[alt*='spring' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    # Sla data-URIs over (te lang voor logo_url kolom)
                    if src.startswith("data:"):
                        continue
                    logo_url = src if src.startswith("http") else BASE_URL + src
                    break
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")
        except Exception as exc:
            logger.warning(f"[spring] Bedrijfsinfo ophalen mislukt: {exc}")
        return {
            "name":          "Spring Kinderopvang",
            "website":       "https://www.spring-kinderopvang.nl",
            "job_board_url": JOBS_URL,
            "scraper_class": "SpringKinderopvangScraper",
            "logo_url":      logo_url,
            "description":   description,
        }

    def fetch_jobs(self) -> list[dict]:
        logger.info(f"[spring] Vacaturelijst ophalen: {JOBS_URL}")
        try:
            resp = requests.get(JOBS_URL, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"[spring] Vacaturelijst ophalen mislukt: {exc}")
            return []

        urls = get_spring_job_urls(resp.text)
        logger.info(f"[spring] {len(urls)} vacature-URLs gevonden")

        jobs = []
        for url in urls:
            job = scrape_spring_job_page(url)
            if job:
                jobs.append(job)
            time.sleep(0.3)

        logger.info(f"[spring] {len(jobs)} vacatures gescraped")
        return jobs
