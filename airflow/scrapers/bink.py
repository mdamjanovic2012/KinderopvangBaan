"""
Bink Kinderopvang scraper — werkenbijbink.nl

Platform: Drupal 11 met JSON-LD JobPosting schema.
Listing URL: https://werkenbijbink.nl/vacatures/
Job URLs:    /vacatures/{slug}

HTML structuur detailpagina:
  Titel: .vacancy-detail--content h2  (of JSON-LD title)
  Stad:  .location p  (of JSON-LD jobLocation.address.addressLocality)
  Uren:  .hours p     (of JSON-LD baseSalary)
  Beschrijving: .contentblocks
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import (
    WordPressJobsScraper,
    extract_job_posting_jsonld,
    parse_job_from_jsonld,
    _parse_hours,
)

logger = logging.getLogger(__name__)


class BinkScraper(WordPressJobsScraper):
    company_slug     = "bink"
    company_name     = "Bink Kinderopvang"
    listing_url      = "https://werkenbijbink.nl/vacatures/"
    website_url      = "https://werkenbijbink.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[bink] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # JSON-LD als primaire bron (Drupal genereert JobPosting schema)
        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            job = parse_job_from_jsonld(url, jsonld)
            # Bink zet city soms in streetAddress i.p.v. addressLocality
            if not job.get("city"):
                loc_el = soup.select_one(".location p")
                if loc_el:
                    job["city"] = loc_el.get_text(strip=True)
                    job["location_name"] = job["city"]
            return job

        # HTML fallback
        h2 = soup.select_one(".vacancy-detail--content h2")
        h1 = soup.find("h1")
        title = (h2 or h1).get_text(strip=True) if (h2 or h1) else ""
        if not title:
            return None

        city = ""
        loc_el = soup.select_one(".location p")
        if loc_el:
            city = loc_el.get_text(strip=True)

        hours_min = hours_max = None
        uren_el = soup.select_one(".hours p")
        if uren_el:
            hours_min, hours_max = _parse_hours(uren_el.get_text(strip=True))

        desc_el = soup.select_one(".contentblocks") or soup.select_one("main")
        desc = desc_el.get_text(separator="\n", strip=True)[:5000] if desc_el else ""

        if hours_min is None:
            hours_min, hours_max = _parse_hours(desc)

        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     city,
            "city":              city,
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
