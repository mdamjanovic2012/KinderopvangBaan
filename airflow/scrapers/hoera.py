"""
Hoera Kindercentra scraper — werkenbijhoera.nl

Platform: WordPress + Elementor + JetEngine.
Listing URL: https://werkenbijhoera.nl/vacancies/
Job URLs:    /vacancies/{slug}/

HTML structuur detailpagina:
  Titel: h1.elementor-heading-title (post-title widget)
  Stad:  body class "location-{slug}" (bijv. "location-hoera-kessel-eik")
         strip "hoera-" prefix → "kessel eik" → .title()
  Uren:  niet als apart getal aanwezig; alleen FTE type (parttime/fulltime)
         → _parse_hours op beschrijving als fallback
  Beschrijving: .elementor-widget-theme-post-content
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

_LOCATION_CLS_RE = re.compile(r"\blocation-([\w\-]+)\b")


class HoeraScraper(WordPressJobsScraper):
    company_slug     = "hoera"
    company_name     = "Hoera Kindercentra"
    listing_url      = "https://werkenbijhoera.nl/vacancies/"
    website_url      = "https://werkenbijhoera.nl"
    job_url_contains = "/vacancies/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[hoera] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.select_one("h1.elementor-heading-title") or soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Stad: body class location-{slug}
        city = ""
        if soup.body:
            body_cls = " ".join(soup.body.get("class", []))
            m = _LOCATION_CLS_RE.search(body_cls)
            if m:
                slug = m.group(1)
                # Strip "hoera-" prefix
                slug = re.sub(r"^hoera-", "", slug)
                city = slug.replace("-", " ").title()

        # Beschrijving
        desc_el = (
            soup.select_one(".elementor-widget-theme-post-content")
            or soup.select_one("main")
            or soup.select_one("article")
        )
        desc = desc_el.get_text(separator="\n", strip=True)[:5000] if desc_el else ""

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
