"""
De Eerste Stap — werkenbijdeeerstestap.nl

Platform: WordPress custom post type 'vacature'.
Taxonomy klassen op <article>: vacature-locatie-{stad}
entry-content eerste <ul>:
  li[0] → postcode + stad + adres (bijv. "6602 XA Wijchen | Blauwe Hof")
  li[1] → uren (bijv. "28-36 uur")
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

_POSTCODE_CITY_RE = re.compile(r"\d{4}\s*[A-Z]{2}\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{1,25})")


class DeEersteStapScraper(WordPressJobsScraper):
    company_slug     = "de-eerste-stap"
    company_name     = "De Eerste Stap"
    listing_url      = "https://werkenbijdeeerstestap.nl/vacatures"
    website_url      = "https://werkenbijdeeerstestap.nl"
    job_url_contains = "/vacature/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[de-eerste-stap] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Location text from first <ul> first <li>: "6602 XA Wijchen | Blauwe Hof"
        location_name = city = ""
        content = soup.select_one(".entry-content")
        hours_min = hours_max = None
        if content:
            first_ul = content.find("ul")
            if first_ul:
                items = first_ul.find_all("li")
                if items:
                    location_name = items[0].get_text(strip=True)
                    m = _POSTCODE_CITY_RE.search(location_name)
                    if m:
                        city = m.group(1)
                if len(items) >= 2:
                    hours_min, hours_max = _parse_hours(items[1].get_text(strip=True))

        # Fallback: article taxonomy class "vacature-locatie-wijchen" → "Wijchen"
        # Only use for short single-word city names (not "kindcentrum-westwijzer")
        if not city:
            article = soup.find("article")
            if article:
                for cls in article.get("class", []):
                    if re.match(r"vacature-locatie-[a-z]{3,}$", cls):
                        raw = cls.replace("vacature-locatie-", "")
                        if "-" not in raw:  # single word = likely a city
                            city = raw.title()
                        break

        # Description
        desc = content.get_text(separator="\n", strip=True)[:5000] if content else ""
        if not desc:
            main = soup.select_one("main")
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
            "location_name":     location_name or city,
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
