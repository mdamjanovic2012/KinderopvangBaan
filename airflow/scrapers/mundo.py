"""
Mundo Kinderopvang — werkenbijmundo.nl

Job links zijn single-segment (geen /vacatures/ patroon).
Alle job links staan direct op de homepage.
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS
from scrapers.wordpress_jobs import extract_job_posting_jsonld, parse_job_from_jsonld, _parse_hours

logger = logging.getLogger(__name__)

BASE_URL     = "https://www.werkenbijmundo.nl"
LISTING_URL  = "https://www.werkenbijmundo.nl/"
SKIP_PATHS   = {"", "/", "/stage", "/contact", "/over-ons"}


class MundoScraper(BaseScraper):
    company_slug = "mundo"
    company_name = "Mundo Kinderopvang"

    def fetch_company(self) -> dict:
        return {
            "name":          self.company_name,
            "website":       BASE_URL,
            "job_board_url": LISTING_URL,
            "scraper_class": "MundoScraper",
            "logo_url":      "",
            "description":   "",
        }

    def _get_job_urls(self) -> list[str]:
        try:
            resp = requests.get(LISTING_URL, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Listing mislukt: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("/"):
                href = BASE_URL.rstrip("/") + href
            if not href.startswith(BASE_URL):
                continue
            path = href.replace(BASE_URL, "").rstrip("/")
            if path in SKIP_PATHS or not path:
                continue
            if href not in seen:
                seen.add(href)
                links.append(href)
        return links

    def fetch_jobs(self) -> list[dict]:
        urls = self._get_job_urls()
        logger.info(f"[{self.company_slug}] {len(urls)} job-URLs gevonden")

        jobs = []
        for url in urls:
            try:
                resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
                resp.raise_for_status()
            except Exception as exc:
                logger.warning(f"[{self.company_slug}] Detailpagina mislukt {url}: {exc}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            jsonld = extract_job_posting_jsonld(soup)
            if jsonld and jsonld.get("title"):
                jobs.append(parse_job_from_jsonld(url, jsonld))
                continue

            h1 = soup.find("h1") or soup.find("h2")
            title = h1.get_text(strip=True) if h1 else ""
            if not title:
                continue

            main = soup.select_one("main") or soup.select_one("article") or soup.body
            desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
            hours_min, hours_max = _parse_hours(desc)
            external_id = url.rstrip("/").split("/")[-1]

            jobs.append({
                "source_url":        url,
                "external_id":       external_id,
                "title":             title,
                "short_description": desc[:300],
                "description":       desc,
                "location_name":     "",
                "city":              "",
                "salary_min":        None,
                "salary_max":        None,
                "hours_min":         hours_min,
                "hours_max":         hours_max,
                "age_min":           None,
                "age_max":           None,
                "contract_type":     "",
                "job_type":          "",
            })

        logger.info(f"[{self.company_slug}] {len(jobs)} vacatures gescraped")
        return jobs
