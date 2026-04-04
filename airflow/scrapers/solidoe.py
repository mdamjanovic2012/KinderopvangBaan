"""
Solidoe Kinderopvang — solidoe.nl

Platform: WordPress + Elementor.
Detail pagina:
  h1.elementor-heading-title  → title (bevat "(34 uur p.w.)" in de titel)
  [data-widget_type="theme-post-content.default"] .elementor-widget-container
    → eerste <p><strong> = stad
  Uren: regex op H1: r'\((\d+(?:-\d+)?)\s+uur\s+p\.w\.\)'
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

_UREN_RE = re.compile(r"\((\d+(?:\s*[-–]\s*\d+)?)\s+uur\s+p\.?w\.?\)", re.I)


class SolidoeScraper(WordPressJobsScraper):
    company_slug     = "solidoe"
    company_name     = "Solidoe Kinderopvang"
    listing_url      = "https://solidoe.nl/werken-bij-solidoe/vacatures/"
    website_url      = "https://solidoe.nl"
    job_url_contains = "/vacature/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[solidoe] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.select_one("h1.elementor-heading-title") or soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Hours from title: "(34 uur p.w.)" or "(16-24 uur p.w.)"
        hours_min = hours_max = None
        m = _UREN_RE.search(title)
        if m:
            hours_min, hours_max = _parse_hours(m.group(1) + " uur")
            if hours_min is None:
                try:
                    val = int(m.group(1))
                    hours_min = hours_max = val
                except ValueError:
                    pass

        # City: first <p><strong> in post content widget
        city = ""
        content_widget = soup.select_one(
            '[data-widget_type="theme-post-content.default"] .elementor-widget-container'
        )
        if content_widget:
            for p in content_widget.find_all("p"):
                strong = p.find("strong")
                if strong:
                    candidate = strong.get_text(strip=True)
                    # City: short single word, not "Functie", "Uren", "Contract" etc.
                    words = candidate.split()
                    if (
                        candidate
                        and len(candidate) < 35
                        and "?" not in candidate
                        and "!" not in candidate
                        and len(words) <= 3
                        and all(w[0].isupper() for w in words if w)
                        and ":" not in candidate
                        and not re.search(
                            r"\b(wat|wij|jij|jou|het|de|dit|die|hoe|meer|onze|jouw|solidoe|over|mail|functie|uren|contract)\b",
                            candidate, re.I
                        )
                    ):
                        city = candidate
                        break

        # Description
        desc = content_widget.get_text(separator="\n", strip=True)[:5000] if content_widget else ""
        if not desc:
            main = soup.select_one("main") or soup.select_one("article")
            desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
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
