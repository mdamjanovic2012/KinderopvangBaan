"""
Humankind scraper — werkenbijhumankind.nl

Platform: Drupal with schema.org JobPosting JSON-LD.
URL pattern: /vacatures/{id}
Listing: Drupal Views AJAX endpoint /views/ajax?view_name=vacancy_index
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import (
    WordPressJobsScraper,
    parse_job_from_jsonld,
    extract_job_posting_jsonld,
    _parse_hours,
)
from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL  = "https://www.werkenbijhumankind.nl"
JOBS_URL  = f"{BASE_URL}/vacatures/"

# Drupal Views AJAX endpoint
AJAX_URL  = f"{BASE_URL}/views/ajax"
AJAX_PARAMS = {
    "view_name":       "vacancy_index",
    "view_display_id": "overview",
    "view_base_path":  "",
}

MAX_PAGES = 35

_AJAX_HEADERS = {
    **SCRAPER_HEADERS,
    "X-Requested-With": "XMLHttpRequest",
    "Accept":           "application/json, text/plain, */*",
}


def _extract_urls_from_ajax(json_data: list) -> list[str]:
    """Extract /vacatures/{id} URLs from Drupal AJAX response."""
    for item in json_data:
        if isinstance(item, dict) and item.get("command") == "insert":
            html = item.get("data", "")
            # URLs may be relative (/vacatures/123) or absolute
            relative = re.findall(r'(?:href=["\'])?/vacatures/(\d+)', html)
            return [f"{BASE_URL}/vacatures/{id_}" for id_ in dict.fromkeys(relative)]
    return []


class HumankindScraper(WordPressJobsScraper):
    company_slug     = "humankind"
    company_name     = "Humankind Kinderopvang"
    listing_url      = JOBS_URL
    website_url      = BASE_URL
    job_url_contains = "/vacatures/"

    def _get_all_job_urls(self) -> list[str]:
        """Collect job URLs via Drupal Views AJAX (JavaScript-rendered listing)."""
        all_urls: set[str] = set()

        for page in range(MAX_PAGES):
            params = {**AJAX_PARAMS, "page": page}
            try:
                resp = requests.get(AJAX_URL, params=params, headers=_AJAX_HEADERS, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                urls = _extract_urls_from_ajax(data)
                new = [u for u in urls if u not in all_urls]
                if not new:
                    logger.info(f"[humankind] No new URLs on page {page}, stopping")
                    break
                all_urls.update(new)
                logger.info(f"[humankind] Page {page}: {len(new)} new links ({len(all_urls)} total)")
            except Exception as exc:
                logger.warning(f"[humankind] AJAX page {page} failed: {exc}")
                break

        return list(all_urls)

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[humankind] Detail page failed {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            job = parse_job_from_jsonld(url, jsonld)
            # Hours fallback from title (e.g. "PM BSO - 20 uur per week")
            if not job.get("hours_min"):
                h_min, h_max = _parse_hours(job.get("title", ""))
                if h_min:
                    job["hours_min"] = h_min
                    job["hours_max"] = h_max
            return job

        # HTML fallback
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        main = soup.select_one("main") or soup.select_one("article")
        desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
        hours_min, hours_max = _parse_hours(title) or _parse_hours(desc)
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
