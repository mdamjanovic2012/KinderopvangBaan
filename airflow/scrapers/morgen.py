"""
Kinderopvang Morgen — kinderopvangmorgen.nl

Platform: WordPress, post type 'vacatures'.
Listing URL: https://www.kinderopvangmorgen.nl/vacatures/
Job URLs:    /vacatures/{slug}/

HTML structuur detailpagina:
  Titel: h1[lang="nl"]
  Stad:  .vacancy-details .icn-pin + div   (sibling div na location-pin SVG)
  Uren:  .vacancy-details .icn-clock + div (sibling div na clock SVG)
  Beschrijving: .vacancy-content-wrap
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class MorgenScraper(WordPressJobsScraper):
    company_slug     = "morgen"
    company_name     = "Kinderopvang Morgen"
    listing_url      = "https://www.kinderopvangmorgen.nl/vacatures/"
    website_url      = "https://www.kinderopvangmorgen.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[morgen] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1", attrs={"lang": "nl"}) or soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Stad: sibling <div> direct na .icn-pin
        city = ""
        icn_pin = soup.select_one(".vacancy-details .icn-pin")
        if icn_pin:
            sibling = icn_pin.find_next_sibling("div")
            if sibling:
                city = sibling.get_text(strip=True)

        # Uren: sibling <div> direct na .icn-clock
        hours_min = hours_max = None
        icn_clock = soup.select_one(".vacancy-details .icn-clock")
        if icn_clock:
            sibling = icn_clock.find_next_sibling("div")
            if sibling:
                hours_min, hours_max = _parse_hours(sibling.get_text(strip=True))

        # Beschrijving
        desc_el = soup.select_one(".vacancy-content-wrap") or soup.select_one("main")
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
