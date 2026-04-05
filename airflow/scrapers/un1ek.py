"""
Un1ek Kinderopvang scraper — www.un1ek.nl

Platform: Custom CMS (The MindOffice), server-side HTML.
Listing URL: https://www.un1ek.nl/vacatures
Job URLs:    https://www.un1ek.nl/{numeric_id}  (bijv. /279, /153)

Aanpak:
  1. Fetch listing page, zoek alle hrefs die overeenkomen met patroon /digits
  2. Per detailpagina: og:title als primaire titelbron, USP-blok voor uren en locatie
  3. Uren worden geëxtraheerd via _parse_hours uit wordpress_jobs
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS
from scrapers.wordpress_jobs import _parse_hours

_FTE_RE = re.compile(r"([\d,\.]+)\s*[-–]\s*([\d,\.]+)\s*fte", re.I)
_FTE_SINGLE_RE = re.compile(r"([\d,\.]+)\s*fte", re.I)


def _parse_fte_as_hours(text: str) -> tuple[int | None, int | None]:
    """Convert FTE to hours (1 fte = 40 uur)."""
    m = _FTE_RE.search(text)
    if m:
        lo = round(float(m.group(1).replace(",", ".")) * 40)
        hi = round(float(m.group(2).replace(",", ".")) * 40)
        return lo, hi
    m = _FTE_SINGLE_RE.search(text)
    if m:
        val = round(float(m.group(1).replace(",", ".")) * 40)
        return val, val
    return None, None

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

        # Title: use og:title (clean), strip " - UN1EK" suffix
        og = soup.find("meta", property="og:title")
        title = og["content"].strip() if og and og.get("content") else ""
        if not title:
            # Fallback: 3rd h1 (first two are the site header "Werken bij UN1EK")
            h1s = soup.find_all("h1")
            title = h1s[2].get_text(strip=True) if len(h1s) >= 3 else (
                h1s[-1].get_text(strip=True) if h1s else ""
            )
        # Strip " - UN1EK" suffix from og:title
        title = re.sub(r"\s*[-–]\s*UN1EK\s*$", "", title, flags=re.I)
        if not title:
            logger.debug(f"[{self.company_slug}] Geen titel gevonden op {url}, overgeslagen")
            return None

        # USPs: [0] startdatum, [1] uren, [2] locatie
        usp_divs = soup.select(".vacature-single__usps > div .content")
        hours_min = hours_max = None
        location_name = ""
        if len(usp_divs) >= 2:
            usp_hours_text = usp_divs[1].get_text(strip=True)
            hours_min, hours_max = _parse_hours(usp_hours_text)
            if hours_min is None:
                hours_min, hours_max = _parse_fte_as_hours(usp_hours_text)
        if len(usp_divs) >= 3:
            location_name = usp_divs[2].get_text(strip=True)

        # Description: intro + content blocks
        desc_parts = []
        for sel in [".vacature-single__intro", ".vacature-single__block",
                    ".vacature-single__conditions"]:
            for el in soup.select(sel):
                text = el.get_text(separator="\n", strip=True)
                if text:
                    desc_parts.append(text)
        desc = "\n\n".join(desc_parts)[:5000]
        if not desc:
            fallback = (
                soup.select_one("section.vacature-single")
                or soup.select_one("main")
                or soup.select_one("article")
            )
            desc = fallback.get_text(separator="\n", strip=True)[:5000] if fallback else ""
        if hours_min is None:
            hours_min, hours_max = _parse_hours(desc)

        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     location_name,
            "city":              "",
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
