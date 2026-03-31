"""
WordPressJobsScraper — basis voor WordPress job sites met schema.org JobPosting.

Aanpak:
  1. Haal vacaturelijst op van listing URL (HTML)
  2. Extraheer job-links via CSS selectors of URL patroon
  3. Scrape elke detailpagina en extraheer JobPosting JSON-LD
  4. Fallback: HTML parsing als JSON-LD ontbreekt

Subclass moet instellen:
  company_slug    — slug in jobs_company tabel
  company_name    — officiële naam
  listing_url     — URL van de vacaturepagina
  website_url     — hoofdwebsite URL
  job_url_pattern — regex om job-URLs te herkennen (bijv. r'/vacatures/[^/]+-\d+/')

Optioneel te overriden:
  job_url_pattern_is_regex — True als het een regex is
  extra_listing_urls       — extra listingpagina's (bijv. voor meerdere categorieën)
"""

import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

EMPLOYMENT_TYPE_MAP = {
    "FULL_TIME":    "fulltime",
    "PART_TIME":    "parttime",
    "CONTRACTOR":   "temp",
    "TEMPORARY":    "temp",
    "INTERN":       "parttime",
    "VOLUNTEER":    "",
    "PER_DIEM":     "temp",
    "OTHER":        "",
}


def _salary_val(raw) -> float | None:
    """Converteert salaris waarde (int, float of None) naar float."""
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _parse_hours(text: str) -> tuple[int | None, int | None]:
    r"""Zoek uren in tekst: '24-32 uur' of '24 uur'."""
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*uur", text, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    m1 = re.search(r"\b(\d+)\s*uur\b", text, re.I)
    if m1:
        v = int(m1.group(1))
        return v, v
    return None, None


def _strip_html(html: str) -> str:
    """Verwijder HTML tags."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n", strip=True)[:5000]


def extract_job_posting_jsonld(soup: BeautifulSoup) -> dict | None:
    """
    Extraheer eerste schema.org JobPosting JSON-LD uit een pagina.
    Geeft ruwe dict of None terug.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return data
            # Soms is het een @graph met meerdere types
            if isinstance(data, dict) and "@graph" in data:
                for item in data["@graph"]:
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        return item
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def parse_job_from_jsonld(url: str, jsonld: dict) -> dict:
    """
    Vertaal een JobPosting JSON-LD dict naar een jobs_job-compatibel dict.
    """
    title = jsonld.get("title", "").strip()

    # Locatie (eerste jobLocation)
    city = postcode = ""
    locations = jsonld.get("jobLocation", [])
    if isinstance(locations, dict):
        locations = [locations]
    if locations:
        addr = locations[0].get("address", {})
        city = addr.get("addressLocality", "").strip()
        postcode = addr.get("postalCode", "").replace(" ", "").strip()

    # Salaris
    salary_min = salary_max = None
    base_salary = jsonld.get("baseSalary", {})
    if base_salary:
        val = base_salary.get("value", {})
        if isinstance(val, dict):
            salary_min = _salary_val(val.get("minValue"))
            salary_max = _salary_val(val.get("maxValue"))

    # Contract type
    emp_types = jsonld.get("employmentType", [])
    if isinstance(emp_types, str):
        emp_types = [emp_types]
    contract_type = ""
    for et in emp_types:
        ct = EMPLOYMENT_TYPE_MAP.get(et.upper(), "")
        if ct:
            contract_type = ct
            break

    # Beschrijving
    desc_raw = jsonld.get("description", "")
    desc = _strip_html(desc_raw) if desc_raw else ""

    # Uren (uit beschrijving)
    hours_min, hours_max = _parse_hours(desc)

    # External ID
    identifier = jsonld.get("identifier", {})
    external_id = ""
    if isinstance(identifier, dict):
        external_id = str(identifier.get("value", "")).strip()
    if not external_id:
        external_id = url.rstrip("/").split("/")[-1]

    return {
        "source_url":        url,
        "external_id":       external_id,
        "title":             title,
        "short_description": desc[:300],
        "description":       desc,
        "location_name":     city,
        "city":              city,
        "postcode":          postcode,
        "salary_min":        salary_min,
        "salary_max":        salary_max,
        "hours_min":         hours_min,
        "hours_max":         hours_max,
        "age_min":           None,
        "age_max":           None,
        "contract_type":     contract_type,
        "job_type":          "",
    }


def get_job_links_from_listing(html: str, base_url: str, job_url_contains: str) -> list[str]:
    """
    Extraheer job-links uit een listingpagina.
    job_url_contains: string die in de job-URL voor moet komen (bijv. '/vacatures/')
    """
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # Zet relatieve URL om naar absoluut
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        # Controleer of het een job-link is (niet de listingpagina zelf)
        if job_url_contains in href:
            path = href.replace(base_url, "")
            segments = [s for s in path.strip("/").split("/") if s]
            # Job-links hebben minimaal 2 segmenten: vacatures/{slug}
            if len(segments) >= 2 and href not in seen:
                seen.add(href)
                links.append(href)
    return links


class WordPressJobsScraper(BaseScraper):
    """
    Basis WordPress scraper met JSON-LD JobPosting extractie.
    Subclass moet company_slug, company_name, listing_url, website_url instellen.
    """

    company_slug:      str = ""
    company_name:      str = ""
    listing_url:       str = ""
    website_url:       str = ""
    job_url_contains:  str = "/vacatures/"
    extra_listing_urls: list[str] = []

    def fetch_company(self) -> dict:
        logo_url = description = ""
        try:
            resp = requests.get(self.website_url, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for sel in ["header img[src]", ".logo img[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    if src.startswith("data:"):
                        continue
                    logo_url = src if src.startswith("http") else self.website_url.rstrip("/") + src
                    if len(logo_url) > 199:
                        logo_url = ""
                    break
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Bedrijfsinfo ophalen mislukt: {exc}")
        return {
            "name":          self.company_name,
            "website":       self.website_url,
            "job_board_url": self.listing_url,
            "scraper_class": self.__class__.__name__,
            "logo_url":      logo_url,
            "description":   description,
        }

    def _get_all_job_urls(self) -> list[str]:
        """Haal alle job-URLs op van de listingpagina(s)."""
        all_urls = set()
        for url in [self.listing_url] + self.extra_listing_urls:
            try:
                resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=30)
                resp.raise_for_status()
                links = get_job_links_from_listing(resp.text, self.website_url, self.job_url_contains)
                all_urls.update(links)
                logger.info(f"[{self.company_slug}] {len(links)} links van {url}")
            except Exception as exc:
                logger.warning(f"[{self.company_slug}] Listingpagina mislukt {url}: {exc}")
        return list(all_urls)

    def _scrape_job_page(self, url: str) -> dict | None:
        """Scrape één job detailpagina, gebruik JSON-LD of HTML fallback."""
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Probeer JSON-LD eerst
        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            return parse_job_from_jsonld(url, jsonld)

        # HTML fallback
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        main = soup.select_one("main") or soup.select_one("article") or soup.select_one(".entry-content")
        desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
        hours_min, hours_max = _parse_hours(desc)
        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     "",
            "city":              "",
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }

    def fetch_jobs(self) -> list[dict]:
        urls = self._get_all_job_urls()
        logger.info(f"[{self.company_slug}] Totaal {len(urls)} job-URLs")

        jobs = []
        for url in urls:
            job = self._scrape_job_page(url)
            if job:
                jobs.append(job)
            time.sleep(0.3)

        logger.info(f"[{self.company_slug}] {len(jobs)} vacatures gescraped")
        return jobs
