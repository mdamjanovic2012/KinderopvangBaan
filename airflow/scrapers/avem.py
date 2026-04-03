"""
AVEM Kinderopvang scraper — avem-kinderopvang.nl

Platform: Mercash .NET portal (mogelijk JS-rendered).
Portal:   https://avem.mercash.nl/Mportal/Vacatures/Overzicht
Hoofd:    https://www.avem-kinderopvang.nl

Aanpak: WordPressJobsScraper met overschreven _get_all_job_urls voor
case-insensitive matching op /Vacature/ of /vacature/ in Mercash-URLs.

Als de portal JS-rendering vereist en de HTML geen links bevat,
logt de scraper een waarschuwing en geeft een lege lijst terug —
geen crash, geen fout.
"""

import logging
import re
import time

import requests
import urllib3
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import (
    WordPressJobsScraper,
    extract_job_posting_jsonld,
    parse_job_from_jsonld,
    _parse_hours,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

PORTAL_URL  = "https://avem.mercash.nl/Mportal/Vacatures/Overzicht"
WEBSITE_URL = "https://www.avem-kinderopvang.nl"
PORTAL_BASE = "https://avem.mercash.nl"

# Mercash detail-URLs bevatten /Vacature/ (hoofdletter) of /vacature/
_VACATURE_RE = re.compile(r"/[Vv]acature/", re.IGNORECASE)


class AvemScraper(WordPressJobsScraper):
    company_slug     = "avem"
    company_name     = "AVEM Kinderopvang"
    listing_url      = PORTAL_URL
    website_url      = WEBSITE_URL
    job_url_contains = "/Vacature/"   # standaard; overschreven in _get_all_job_urls

    # ── Flexibele URL-verzameling ────────────────────────────────────────────

    def _get_all_job_urls(self) -> list[str]:
        """
        Overschrijft de basisimplementatie voor case-insensitive Mercash-URLs.
        Probeert de portal te fetchen met requests; als de HTML leeg is of
        geen vacature-links bevat (JS-rendering), geeft een lege lijst terug.
        """
        try:
            resp = requests.get(PORTAL_URL, headers=SCRAPER_HEADERS, timeout=30, verify=False)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Portal niet bereikbaar: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen: set[str] = set()
        urls: list[str] = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()

            # Zet relatieve URL om naar absoluut (Mercash gebruikt relatieve paden)
            if href.startswith("/"):
                href = PORTAL_BASE.rstrip("/") + href

            # Case-insensitive check op /Vacature/ of /vacature/
            if _VACATURE_RE.search(href) and href not in seen:
                # Sla de listing-URL zelf niet op
                if href.rstrip("/").lower() != PORTAL_URL.rstrip("/").lower():
                    seen.add(href)
                    urls.append(href)

        if not urls:
            logger.warning(
                f"[{self.company_slug}] Geen vacature-links gevonden op {PORTAL_URL}. "
                "De Mercash portal kan JS-rendering vereisen; overweeg Playwright/Selenium."
            )
        else:
            logger.info(f"[{self.company_slug}] {len(urls)} vacature-URLs gevonden")

        return urls

    def _scrape_job_page(self, url: str) -> dict | None:
        """Override om verify=False te gebruiken voor avem.mercash.nl."""
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20, verify=False)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            return parse_job_from_jsonld(url, jsonld)

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        main = soup.select_one("main") or soup.select_one(".content") or soup.select_one("article")
        desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
        hours_min, hours_max = _parse_hours(desc)
        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url": url, "external_id": external_id, "title": title,
            "short_description": desc[:300], "description": desc,
            "location_name": "", "city": "", "postcode": "",
            "salary_min": None, "salary_max": None,
            "hours_min": hours_min, "hours_max": hours_max,
            "age_min": None, "age_max": None,
            "contract_type": "", "job_type": "",
        }
