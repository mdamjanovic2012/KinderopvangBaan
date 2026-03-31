"""
EasyCruitScraper — basis voor EasyCruit job board sites (Visma).

EasyCruit is an ATS used by several Dutch childcare companies.
URL pattern: https://{company}.easycruit.com/vacancy/{id}/{sub}?iso=nl

Subclass must set:
  company_slug  — slug in jobs_company table
  company_name  — official name
  easycruit_url — base URL e.g. https://sinne.easycruit.com
  website_url   — main company website
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

HOURS_RE  = re.compile(r"(\d+)\s*(?:tot|[-–])\s*(\d+)\s*uur", re.I)
HOURS1_RE = re.compile(r"\b(\d+)\s*uur\b", re.I)


def _parse_hours(text: str) -> tuple[int | None, int | None]:
    m = HOURS_RE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = HOURS1_RE.search(text)
    if m:
        v = int(m.group(1))
        return v, v
    return None, None


class EasyCruitScraper(BaseScraper):
    company_slug:  str = ""
    company_name:  str = ""
    easycruit_url: str = ""
    website_url:   str = ""

    def fetch_company(self) -> dict:
        logo_url = description = ""
        try:
            resp = requests.get(self.website_url, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for sel in ["header img[src]", ".logo img[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    if src.startswith("data:"):
                        continue
                    logo_url = src if src.startswith("http") else self.website_url.rstrip("/") + src
                    if len(logo_url) > 199:
                        logo_url = ""
                    break
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Company info failed: {exc}")

        return {
            "name":          self.company_name,
            "website":       self.website_url,
            "job_board_url": self.easycruit_url,
            "scraper_class": self.__class__.__name__,
            "logo_url":      logo_url,
            "description":   description,
        }

    def _get_job_urls(self) -> list[str]:
        """Scrape job listing and return unique vacancy URLs."""
        try:
            resp = requests.get(self.easycruit_url, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Listing failed: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/vacancy/" not in href:
                continue
            if href.startswith("/"):
                href = self.easycruit_url.rstrip("/") + href
            # Normalize: strip query params for dedup
            base_href = href.split("?")[0]
            if base_href not in seen:
                seen.add(base_href)
                # Keep iso=nl for proper Dutch content
                urls.append(href if "?" in href else href + "?iso=nl")
        logger.info(f"[{self.company_slug}] {len(urls)} job URLs found")
        return urls

    def _scrape_job_page(self, url: str) -> dict | None:
        """Fetch and parse an EasyCruit vacancy detail page."""
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Detail page failed {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # City from div.jd-location
        city = ""
        loc_el = soup.select_one(".jd-location")
        if loc_el:
            loc_text = loc_el.get_text(strip=True)
            # Format: "Locatie:Amsterdam" or "Locatie:\nAmsterdam"
            city = re.sub(r"^[Ll]ocatie\s*[:]\s*", "", loc_text).strip()

        # Description
        main = soup.select_one("main") or soup.select_one(".jd-content") or soup.select_one("article") or soup
        desc = main.get_text(separator="\n", strip=True)[:5000]

        hours_min, hours_max = _parse_hours(desc)

        # External ID from URL: /vacancy/{id}/{sub}
        parts = url.split("?")[0].rstrip("/").split("/")
        external_id = parts[-2] if len(parts) >= 2 else parts[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     city,
            "city":              city,
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

    def fetch_jobs(self) -> list[dict]:
        urls = self._get_job_urls()
        jobs = []
        for url in urls:
            job = self._scrape_job_page(url)
            if job:
                jobs.append(job)
            time.sleep(0.3)
        logger.info(f"[{self.company_slug}] {len(jobs)} vacatures scraped")
        return jobs
