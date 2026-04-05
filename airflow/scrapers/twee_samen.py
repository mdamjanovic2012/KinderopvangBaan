"""
2Samen scraper — werkenbij2samen.nl

Platform: WordPress. No JSON-LD.
URL pattern: /vacature/{slug} (singular, not /vacatures/).

Page structure:
  p[0]: "Gedempte Sloot 7, Centrum, 2513 TC Den Haag"  (address with postcode)
  p[1]: "14 – 25 uur, BSO, € 2.641 – 3.630 bruto..."  (hours + salary)
  p[n]: description paragraphs
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

_POSTCODE_CITY_RE = re.compile(r"\b(\d{4}\s*[A-Z]{2})\s+([A-Z][A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{1,30})")
_SALARY_RE        = re.compile(r"€\s*([\d.,]+)\s*[-–]\s*€?\s*([\d.,]+)", re.I)


def _parse_euros(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


class TweeSamenScraper(WordPressJobsScraper):
    company_slug     = "2samen"
    company_name     = "2Samen Kinderopvang"
    listing_url      = "https://www.werkenbij2samen.nl/vacatures/"
    website_url      = "https://www.werkenbij2samen.nl"
    job_url_contains = "/vacature/"  # Singular — detail pages are /vacature/{slug}

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[2samen] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Zoek stad en postcode in paragraaf met postkod-patroon
        city = postcode = ""
        for p in soup.find_all("p"):
            txt = p.get_text(strip=True)
            m = _POSTCODE_CITY_RE.search(txt)
            if m:
                postcode = m.group(1).replace(" ", "")
                city = m.group(2).strip()
                break

        # Zoek uren en salaris in paragraaf met "uur"
        hours_min = hours_max = None
        salary_min = salary_max = None
        for p in soup.find_all("p"):
            txt = p.get_text(strip=True)
            if "uur" in txt.lower() and "–" in txt:
                hm = _parse_hours(re.sub(r"–", "-", txt))
                if hm[0] is not None:
                    hours_min, hours_max = hm
                sm = _SALARY_RE.search(txt)
                if sm:
                    salary_min = _parse_euros(sm.group(1))
                    salary_max = _parse_euros(sm.group(2))
                break

        # Beschrijving
        main = soup.select_one("main") or soup.select_one("article") or soup.select_one(".entry-content")
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
            "location_name":     f"{postcode} {city}".strip() if postcode else city,
            "city":              city,
            "postcode":          postcode,
            "salary_min":        salary_min,
            "salary_max":        salary_max,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
