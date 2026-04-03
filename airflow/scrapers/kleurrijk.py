"""
CKO KleurRijk scraper — kleurrijkkinderopvang.nl

Detail pages hebben geen H1, alleen H2 als vacature-titel.
Override _scrape_job_page om H2 te gebruiken als H1 ontbreekt.
"""

import logging

import requests
from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, extract_job_posting_jsonld, _parse_hours

logger = logging.getLogger(__name__)


class KleurrijkScraper(WordPressJobsScraper):
    company_slug     = "kleurrijk"
    company_name     = "CKO KleurRijk"
    listing_url      = "https://www.kleurrijkkinderopvang.nl/vacatures/"
    website_url      = "https://www.kleurrijkkinderopvang.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Detailpagina mislukt {url}: {exc}")
            return None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")

        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            from scrapers.wordpress_jobs import parse_job_from_jsonld
            return parse_job_from_jsonld(url, jsonld)

        # HTML fallback: gebruik H1 of H2
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
