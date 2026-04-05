"""
Kinderopvang Friesland scraper — kinderopvangfriesland.nl

Platform: WordPress met SKF custom theme.
Listing URL: https://www.kinderopvangfriesland.nl/vacatures/
Job URLs:    /vacatures/{slug}/

HTML structuur detailpagina (.hero-single):
  Titel: .hero-single h1
  Stad:  .label-container .label met FontAwesome fa-map-marker icon
  Uren:  .label-container .label met FontAwesome fa-clock icon
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class KoFrieslandScraper(WordPressJobsScraper):
    company_slug     = "ko-friesland"
    company_name     = "Kinderopvang Friesland"
    listing_url      = "https://www.kinderopvangfriesland.nl/vacatures/"
    website_url      = "https://www.kinderopvangfriesland.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[ko-friesland] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        hero = soup.select_one(".hero-single, .hero.hero-single")
        h1 = hero.find("h1") if hero else soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        city = ""
        hours_min = hours_max = None

        for label in soup.select(".label-container .label, .label-container span.label"):
            icon = label.find("i")
            if not icon:
                continue
            icon_cls = " ".join(icon.get("class", []))
            text = label.get_text(strip=True)
            if "fa-map-marker" in icon_cls:
                city = text
            elif "fa-clock" in icon_cls:
                hours_min, hours_max = _parse_hours(text)

        # Beschrijving
        desc_el = (
            soup.select_one(".content.single-vacancie #content")
            or soup.select_one(".content.single-vacancie")
            or soup.select_one("main")
        )
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
