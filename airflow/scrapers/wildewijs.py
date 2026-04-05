"""
Wilde Wijs Kinderopvang scraper — werkenbij.kinderopvangwildewijs.nl

Platform: Umbraco CMS (VWA Digital, niet WordPress).
Listing URL: https://werkenbij.kinderopvangwildewijs.nl/vacatures/
Job URLs:    /vacatures/{slug}/

HTML structuur detailpagina:
  Titel:       .header-job-offer h1
  Stad:        .header-job-offer .icons p > i.icon-location  (tekst van de <p>)
  Uren:        .header-job-offer .icons p > i.icon-clock     (tekst van de <p>)
  Beschrijving: div.rte
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class WildewijsScraper(WordPressJobsScraper):
    company_slug     = "wildewijs"
    company_name     = "Wilde Wijs Kinderopvang"
    listing_url      = "https://werkenbij.kinderopvangwildewijs.nl/vacatures/"
    website_url      = "https://werkenbij.kinderopvangwildewijs.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[wildewijs] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        header = soup.select_one(".header-job-offer")
        h1 = header.find("h1") if header else soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        city = ""
        hours_min = hours_max = None

        if header:
            icons_div = header.select_one(".icons")
            if icons_div:
                for p in icons_div.find_all("p"):
                    icon = p.find("i")
                    if not icon:
                        continue
                    icon_cls = " ".join(icon.get("class", []))
                    text = p.get_text(strip=True)
                    if "icon-location" in icon_cls:
                        city = text
                    elif "icon-clock" in icon_cls:
                        hours_min, hours_max = _parse_hours(text)

        # Beschrijving
        desc_parts = []
        for rte in soup.select("div.rte"):
            t = rte.get_text(separator="\n", strip=True)
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
