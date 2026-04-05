"""
Sport-BSO Flekss scraper — flekss.nl

Platform: WordPress + Elementor + JetEngine.
REST API:  /wp-json/wp/v2/vacatures
Job URLs:  /vacatures/{slug}/

HTML structuur detailpagina:
  Titel: h1.elementor-heading-title
  Uren:  .elementor-inline-items .elementor-icon-list-item met fa-clock icon
  Stad:  body class "locatie-plaats-{city-slug}" (taxonomy, vaak leeg)
  Beschrijving: .elementor-widget-theme-post-content
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressRestApiScraper, _parse_hours

logger = logging.getLogger(__name__)

_LOCATIE_PLAATS_RE = re.compile(r"\blocatie-plaats-([\w\-]+)\b")


class FlekssScraper(WordPressRestApiScraper):
    company_slug      = "flekss"
    company_name      = "Sport-BSO Flekss"
    website_url       = "https://flekss.nl"
    wp_rest_post_type = "vacatures"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[flekss] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.select_one("h1.elementor-heading-title") or soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Uren: zoek icon-list item met klok-icoon
        hours_min = hours_max = None
        for item in soup.select(".elementor-inline-items .elementor-icon-list-item"):
            icon = item.select_one("i")
            if icon and "fa-clock" in " ".join(icon.get("class", [])):
                text_el = item.select_one(".elementor-icon-list-text")
                if text_el:
                    uren_norm = re.sub(r"\btot\b", "-", text_el.get_text(strip=True), flags=re.I)
                    hours_min, hours_max = _parse_hours(uren_norm)
                    break

        # Stad: body class "locatie-plaats-{slug}"
        city = ""
        if soup.body:
            body_cls = " ".join(soup.body.get("class", []))
            m = _LOCATIE_PLAATS_RE.search(body_cls)
            if m:
                city = m.group(1).replace("-", " ").title()

        # Beschrijving
        desc_el = (
            soup.select_one(".elementor-widget-theme-post-content")
            or soup.select_one("main")
            or soup.select_one("article")
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
