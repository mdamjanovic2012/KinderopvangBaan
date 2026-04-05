"""
SKDD Kinderopvang scraper — werkenbijskdd.nl

Platform: WordPress met custom CSS klassen voor job metadata.
Gestructureerde velden in div.row.opsom:
  span.field-value.locatieveld  → stad (bijv. "Leersum")
  span.field-value.urenveld     → uren (bijv. "13,25" of "32 uur")
  span.field-value.soortopvangveld → type opvang (bijv. "BSO")
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


def _parse_skdd_hours(text: str) -> tuple[int | None, int | None]:
    """Parse hours from SKDD: "32 uur" or decimal "13,25" or "16-24 uur"."""
    h_min, h_max = _parse_hours(text)
    if h_min is not None:
        return h_min, h_max
    # Decimal format: "13,25" → 13 uur
    m = re.match(r"^([\d,\.]+)$", text.strip())
    if m:
        try:
            val = round(float(m.group(1).replace(",", ".")))
            return val, val
        except ValueError:
            pass
    return None, None


class SkddScraper(WordPressJobsScraper):
    company_slug     = "skdd"
    company_name     = "SKDD Kinderopvang"
    listing_url      = "https://www.werkenbijskdd.nl/vacatures"
    website_url      = "https://www.werkenbijskdd.nl"
    job_url_contains = "/vacatures"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[skdd] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # H1 is site header "Vacatures" — real title is in H2
        h2 = soup.find("h2")
        title = h2.get_text(strip=True) if h2 else ""
        if not title:
            # Fallback: <title> tag, strip " - Werken bij SKDD" suffix
            title_tag = soup.find("title")
            if title_tag:
                title = re.sub(r"\s*-\s*Werken bij SKDD\s*$", "", title_tag.get_text(strip=True), flags=re.I)
        if not title:
            return None

        # Structured meta fields
        city = ""
        loc_el = soup.select_one("span.field-value.locatieveld")
        if loc_el:
            city = loc_el.get_text(strip=True)

        hours_min = hours_max = None
        uren_el = soup.select_one("span.field-value.urenveld")
        if uren_el:
            hours_min, hours_max = _parse_skdd_hours(uren_el.get_text(strip=True))

        # Description
        main = soup.select_one("main") or soup.select_one("article") or soup.select_one(".entry-content")
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
