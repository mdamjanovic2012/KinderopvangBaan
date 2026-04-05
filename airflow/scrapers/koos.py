"""
Kinderopvang KOOS scraper — kinderopvangkoos.nl

Platform: WordPress + WPBakery Page Builder + Rank Math SEO.
Listing URL: https://www.kinderopvangkoos.nl/werken-bij/
Job URLs:    /vacature/{slug}/   (CPT: vacature — let op: enkelvoud)

HTML structuur detailpagina:
  Titel: .titlevacature h1
  Stad:  .boxlocatie p  (naast .boxvoorvoegsel2 "Locatie")
  Uren:  .boxuren       (tekst: "28 - 32 uur per week")
  Beschrijving: .wpb_text_column .wpb_wrapper
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class KoosScraper(WordPressJobsScraper):
    company_slug     = "koos"
    company_name     = "Kinderopvang KOOS"
    listing_url      = "https://www.kinderopvangkoos.nl/werken-bij/"
    website_url      = "https://www.kinderopvangkoos.nl"
    job_url_contains = "/vacature/"   # enkelvoud CPT slug

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[koos] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        title_sec = soup.select_one(".titlevacature")
        h1 = title_sec.find("h1") if title_sec else soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Stad
        city = ""
        loc_el = soup.select_one(".boxlocatie p") or soup.select_one(".boxlocatie")
        if loc_el:
            city = loc_el.get_text(strip=True)

        # Uren
        hours_min = hours_max = None
        uren_el = soup.select_one(".boxuren")
        if uren_el:
            hours_min, hours_max = _parse_hours(uren_el.get_text(strip=True))

        # Beschrijving
        desc_parts = []
        for el in soup.select(".wpb_text_column .wpb_wrapper"):
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
