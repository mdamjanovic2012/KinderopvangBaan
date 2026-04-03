"""
Puck&Co scraper — puckenco.nl

Job URLs: /werken-bij/{slug}
Detail pages gebruiken H2 als titel (geen H1, geen JSON-LD).
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, extract_job_posting_jsonld, \
    parse_job_from_jsonld, _parse_hours

logger = logging.getLogger(__name__)


class PuckcoScraper(WordPressJobsScraper):
    company_slug     = "puckco"
    company_name     = "Puck&Co"
    listing_url      = "https://www.puckenco.nl/werken-bij"
    website_url      = "https://www.puckenco.nl"
    job_url_contains = "/werken-bij/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            return parse_job_from_jsonld(url, jsonld)

        heading = soup.find("h1") or soup.find("h2")
        title = heading.get_text(strip=True) if heading else ""
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
