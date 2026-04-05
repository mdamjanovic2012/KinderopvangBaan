"""
De Lange Keizer scraper — delangekeizer.nl

Platform: WordPress + WPBakery Page Builder.
Listing URL: https://delangekeizer.nl/personeel/vacatures/
Job URLs:    /personeel/vacatures/{slug}

HTML structuur detailpagina:
  Titel: h1.vc_custom_heading  (strip "Vacature: " prefix)
  Stad:  niet als apart HTML-veld; city/uren via regex op body tekst
  Uren:  regex op body tekst (bijv. "12 uur (ma, di, do)")
  Beschrijving: .nz-column-text
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

# Locatie-optie in de CF7 select bevat "{Naam locatie}, {Stad}"
_LOCATIE_OPTION_RE = re.compile(
    r"(?:locatie|vestiging)[^\n]*?([A-Z][A-Za-zÀ-ÿ\s\-]{2,30}?)(?:\s*[,|\n]|$)",
    re.I,
)


class DeLangeKeizerScraper(WordPressJobsScraper):
    company_slug     = "de-lange-keizer"
    company_name     = "De Lange Keizer"
    listing_url      = "https://delangekeizer.nl/personeel/vacatures/"
    website_url      = "https://delangekeizer.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[de-lange-keizer] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.select_one("h1.vc_custom_heading") or soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        # Strip "Vacature: " prefix
        title = re.sub(r"^[Vv]acature:\s*", "", title).strip()
        if not title:
            return None

        # Beschrijving: WPBakery nz-column-text blokken
        desc_parts = []
        for el in soup.select(".nz-column-text"):
            t = el.get_text(separator="\n", strip=True)
            if t:
                desc_parts.append(t)
        desc = "\n\n".join(desc_parts)[:5000]
        if not desc:
            main = soup.select_one("main") or soup.select_one("article")
            desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""

        hours_min, hours_max = _parse_hours(desc)

        # Stad: zoek in CF7 select options of body tekst
        city = ""
        for opt in soup.select("select[name='welke-locatie'] option"):
            val = opt.get_text(strip=True)
            if "," in val:
                city = val.split(",")[-1].strip()
                break

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
