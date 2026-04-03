"""
Un1ek Kinderopvang scraper — www.un1ek.nl

Platform: Custom CMS (The MindOffice), server-side HTML.
Listing URL: https://www.un1ek.nl/vacatures
Job URLs:    https://www.un1ek.nl/{numeric_id}  (bijv. /279, /153)

Aanpak:
  1. Fetch listing page, zoek alle hrefs die overeenkomen met r'/\d+$'
  2. Per detailpagina: probeer JSON-LD JobPosting, fallback naar HTML h1 + main/article
  3. Uren worden geëxtraheerd via _parse_hours uit wordpress_jobs
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS
from scrapers.wordpress_jobs import (
    _parse_hours,
    _strip_html,
    extract_job_posting_jsonld,
    parse_job_from_jsonld,
)

logger = logging.getLogger(__name__)

LISTING_URL = "https://www.un1ek.nl/vacatures"
WEBSITE_URL = "https://www.un1ek.nl"

# Numeric-ID job URL: /279, /153 — exactly one path segment that is all digits
_NUMERIC_ID_RE = re.compile(r"^/(\d+)$")


class Un1ekScraper(BaseScraper):
    company_slug = "un1ek"
    company_name = "Un1ek Kinderopvang"

    # ── Bedrijfsinfo ──────────────────────────────────────────────────────────

    def fetch_company(self) -> dict:
        logo_url = description = ""
        try:
            resp = requests.get(WEBSITE_URL, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for sel in ["header img[src]", ".logo img[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    if src.startswith("data:"):
                        continue
                    logo_url = src if src.startswith("http") else WEBSITE_URL.rstrip("/") + src
                    if len(logo_url) > 199:
                        logo_url = ""
                    break
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Bedrijfsinfo ophalen mislukt: {exc}")

        return {
            "name":          self.company_name,
            "website":       WEBSITE_URL,
            "job_board_url": LISTING_URL,
            "scraper_class": self.__class__.__name__,
            "logo_url":      logo_url,
            "description":   description,
        }

    # ── Vacature-URLs ophalen ─────────────────────────────────────────────────

    def _get_job_urls(self) -> list[str]:
        """
        Fetcht de listingpagina en verzamelt alle hrefs die voldoen
        aan het patroon /{numeric_id} (één segment, alleen cijfers).
        """
        try:
            resp = requests.get(LISTING_URL, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Listingpagina mislukt: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen: set[str] = set()
        urls: list[str] = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Zet relatieve URL om naar absoluut
            if href.startswith("/"):
                path = href.split("?")[0].split("#")[0]  # strip query/fragment
                if _NUMERIC_ID_RE.match(path) and href not in seen:
                    seen.add(href)
                    urls.append(WEBSITE_URL.rstrip("/") + path)

        logger.info(f"[{self.company_slug}] {len(urls)} job-URLs gevonden op listingpagina")
        return urls

    # ── Detailpagina scraper ──────────────────────────────────────────────────

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Probeer JSON-LD eerst
        jsonld = extract_job_posting_jsonld(soup)
        if jsonld and jsonld.get("title"):
            return parse_job_from_jsonld(url, jsonld)

        # HTML fallback: titel uit h1, beschrijving uit main of article
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            logger.debug(f"[{self.company_slug}] Geen titel gevonden op {url}, overgeslagen")
            return None

        main = (
            soup.select_one("main")
            or soup.select_one("article")
            or soup.select_one(".entry-content")
            or soup.select_one(".content")
        )
        desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
        hours_min, hours_max = _parse_hours(desc)

        # external_id = numeriek ID uit URL
        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     "",
            "city":              "",
            "postcode":          "",
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }

    # ── Hoofdmethode ─────────────────────────────────────────────────────────

    def fetch_jobs(self) -> list[dict]:
        urls = self._get_job_urls()
        logger.info(f"[{self.company_slug}] Totaal {len(urls)} job-URLs")

        jobs = []
        for url in urls:
            job = self._scrape_job_page(url)
            if job:
                jobs.append(job)
            time.sleep(0.3)

        logger.info(f"[{self.company_slug}] {len(jobs)} vacatures gescraped")
        return jobs
