"""
CompaNanny scraper — werkenbijcompananny.nl

Platform: Custom PHP site with schema.org JobPosting JSON-LD.
URL pattern: /vacatures/{city}/{slug} or /vacatures/{slug}

City comes from addressLocality which may include ", Nederlands" suffix — cleaned up.
"""

import re

from scrapers.wordpress_jobs import WordPressJobsScraper, parse_job_from_jsonld, extract_job_posting_jsonld
from scrapers.base import SCRAPER_HEADERS
import requests
from bs4 import BeautifulSoup
import logging
import time

logger = logging.getLogger(__name__)

BASE_URL  = "https://www.werkenbijcompananny.nl"
JOBS_URL  = f"{BASE_URL}/vacatures/"

# Trailing country suffix in addressLocality (e.g. "Amsterdam, Nederlands")
_CITY_SUFFIX_RE = re.compile(r",\s*(Nederlands|Netherlands|NL)\s*$", re.I)


def _clean_city(city: str) -> str:
    """Remove country suffix from city name returned by CompaNanny JSON-LD."""
    return _CITY_SUFFIX_RE.sub("", city).strip()


class CompaNannyScraper(WordPressJobsScraper):
    company_slug     = "compananny"
    company_name     = "CompaNanny"
    listing_url      = JOBS_URL
    website_url      = BASE_URL
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        """Fetch job page, parse JSON-LD, clean up city field."""
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[compananny] Detail page failed {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            job = parse_job_from_jsonld(url, jsonld)
            raw_city = job.get("city", "")
            clean_city = _clean_city(raw_city)
            job["city"] = clean_city
            # Propagate city cleanup into location_name (which may include city)
            if raw_city and raw_city != clean_city and raw_city in job.get("location_name", ""):
                job["location_name"] = job["location_name"].replace(raw_city, clean_city).strip(", ").strip()
            return job

        # HTML fallback
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        main = soup.select_one("main") or soup.select_one("article") or soup.select_one(".entry-content")
        from scrapers.wordpress_jobs import _parse_hours
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
            "postcode":          "",
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
