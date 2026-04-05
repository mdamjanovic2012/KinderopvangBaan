"""
Kinderopvang Purmerend — kinderopvangpurmerend.nl

Platform: WordPress + custom kdvpurmerend theme + ACF blocks.
CPT:       vacatures
REST API:  /wp-json/wp/v2/vacatures
Job URLs:  /vacatures/{slug}-vac{id}/

HTML structuur detailpagina (ACF dw_page_header block):
  Titel: .dw_page_header_title h1
  Uren:  .dw_page_header_categories_col.uren span  (alleen getal, bijv. "8")
  Stad:  .dw_page_header_categories_col.plaatsen span
  Beschrijving: .dw_text_block_content
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressRestApiScraper, _parse_hours

logger = logging.getLogger(__name__)


class KoPurmerendScraper(WordPressRestApiScraper):
    company_slug      = "ko-purmerend"
    company_name      = "Kinderopvang Purmerend"
    website_url       = "https://kinderopvangpurmerend.nl"
    wp_rest_post_type = "vacatures"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[ko-purmerend] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        header = soup.select_one(".dw_page_header_title")
        h1 = header.find("h1") if header else soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Stad
        city = ""
        plaatsen_el = soup.select_one(".dw_page_header_categories_col.plaatsen span")
        if plaatsen_el:
            city = plaatsen_el.get_text(strip=True)

        # Uren: alleen getal (bijv. "8"), voeg "uur" toe voor _parse_hours
        hours_min = hours_max = None
        uren_el = soup.select_one(".dw_page_header_categories_col.uren span")
        if uren_el:
            uren_text = uren_el.get_text(strip=True)
            # Probeer te parsen; als het alleen een getal is, maak er "X uur" van
            hours_min, hours_max = _parse_hours(uren_text)
            if hours_min is None and uren_text.isdigit():
                v = int(uren_text)
                hours_min, hours_max = v, v

        # Beschrijving
        desc_parts = []
        for el in soup.select(".dw_text_block_content"):
            t = el.get_text(separator="\n", strip=True)
            if t:
                desc_parts.append(t)
        desc = "\n\n".join(desc_parts)[:5000]
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
