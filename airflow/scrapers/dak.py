"""
Dak Kindercentra scraper — dakkindercentra.nl

Platform: WordPress. No JSON-LD, no <main>/<article> tags.
Structured location data in custom CSS classes:
  .location-city  → city + district (e.g. "Den Haag Centrum")
  .location-street → street + number
  span.opvangsvorm → location name (e.g. "Dak Adriaan Vlack - Kinderdagverblijf")
  span.hours      → hours (e.g. "24-32 uur")
  span.salary     → salary range (e.g. "€ 2.641- € 3.630 o.b.v. 36 uur")
  .header-text + .content-wrap → description
"""
import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours
from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)

SALARY_RE = re.compile(r"€\s*([\d.,]+)\s*[-–]\s*€?\s*([\d.,]+)", re.I)
# Common district words that are NOT city names
_DISTRICT_WORDS = re.compile(r"\s+(Centrum|Noord|Zuid|West|Oost|Binnenstad|Wijk|Kwartier)$", re.I)


def _parse_euros(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


class DakScraper(WordPressJobsScraper):
    company_slug       = "dak"
    company_name       = "Dak Kindercentra"
    listing_url        = "https://www.dakkindercentra.nl/vacatures/"
    website_url        = "https://www.dakkindercentra.nl"
    job_url_contains   = "/vacatures/"
    extra_listing_urls = [
        "https://www.dakkindercentra.nl/vacatures-servicebureau/",
    ]

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[dak] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Location
        loc_name_el = soup.select_one("span.opvangsvorm")
        loc_city_el = soup.select_one(".location-city")
        loc_street_el = soup.select_one(".location-street")

        location_name = loc_name_el.get_text(strip=True) if loc_name_el else ""
        city_raw = loc_city_el.get_text(strip=True) if loc_city_el else ""
        street = loc_street_el.get_text(strip=True) if loc_street_el else ""

        # Extract city: take 2 words if first is a short particle (Den, De, Het),
        # otherwise just 1 word — strips district/neighborhood suffix
        words = city_raw.split()
        if words:
            city = " ".join(words[:2]) if len(words) > 1 and len(words[0]) <= 3 else words[0]
        else:
            city = ""

        # Hours
        hours_el = soup.select_one("span.hours")
        hours_min, hours_max = _parse_hours(hours_el.get_text(strip=True)) if hours_el else (None, None)

        # Salary
        salary_min = salary_max = None
        salary_el = soup.select_one("span.salary")
        if salary_el:
            sm = SALARY_RE.search(salary_el.get_text(strip=True))
            if sm:
                salary_min = _parse_euros(sm.group(1))
                salary_max = _parse_euros(sm.group(2))

        # Description
        desc_parts = []
        header_el = soup.select_one(".header-text")
        if header_el:
            desc_parts.append(header_el.get_text(separator="\n", strip=True))
        content_el = soup.select_one(".content-wrap") or soup.select_one(".content-inner")
        if content_el:
            desc_parts.append(content_el.get_text(separator="\n", strip=True))
        desc = "\n\n".join(desc_parts)[:5000]

        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     location_name or city_raw,
            "city":              city,
            "street":            street,
            "salary_min":        salary_min,
            "salary_max":        salary_max,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
