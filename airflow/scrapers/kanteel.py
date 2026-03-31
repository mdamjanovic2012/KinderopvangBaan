"""
Kanteel Kinderopvang scraper — werkenbijkanteel.nl

Platform: WordPress with schema.org JobPosting JSON-LD.
SSL certificate issue — requests must use verify=False.
Job URLs use numeric IDs: /vacature/{id}
"""

import logging
import re

import requests
import urllib3
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import WordPressJobsScraper
from scrapers.base import SCRAPER_HEADERS

# Suppress SSL warnings since the site has a cert issue
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

BASE_URL = "https://werkenbijkanteel.nl"
JOBS_URL = f"{BASE_URL}/vacatures/"


class KanteelScraper(WordPressJobsScraper):
    company_slug     = "kanteel"
    company_name     = "Kanteel Kinderopvang"
    listing_url      = JOBS_URL
    website_url      = BASE_URL
    job_url_contains = "/vacature/"

    def _get_all_job_urls(self) -> list[str]:
        """Override to use verify=False and extract numeric /vacature/{id} URLs."""
        try:
            resp = requests.get(self.listing_url, headers=SCRAPER_HEADERS, timeout=30, verify=False)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[kanteel] Listing failed: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("/"):
                href = BASE_URL + href
            # Only keep numeric vacature URLs: /vacature/{digits}
            if not re.search(r"/vacature/\d+", href):
                continue
            if href not in seen:
                seen.add(href)
                links.append(href)

        logger.info(f"[kanteel] {len(links)} job URLs found")
        return links

    def _scrape_job_page(self, url: str):
        """Override to use verify=False for SSL-broken site."""
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20, verify=False)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[kanteel] Detail page failed {url}: {exc}")
            return None

        from bs4 import BeautifulSoup
        from scrapers.wordpress_jobs import (
            extract_job_posting_jsonld,
            parse_job_from_jsonld,
            _parse_hours,
        )

        soup = BeautifulSoup(resp.text, "lxml")
        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            return parse_job_from_jsonld(url, jsonld)

        # HTML fallback
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        main = soup.select_one("main") or soup.select_one("article") or soup
        desc = main.get_text(separator="\n", strip=True)[:5000]
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
