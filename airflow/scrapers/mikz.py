"""
Mikz kinderopvang — mikz.nl (SilverStripe SSR)

Vacature-URL patroon: /werkenenlerenbij/{slug}
Geen JSON-LD, geen standaard WordPress structuur.

Extractie:
  h1.color--header   → title
  titel tussen haakjes bijv. "(Waalwijk)" → city
  .block--brand-sec div.gamma met "Uren per week" → hours
  .intro + .content  → description
"""
import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours
from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)

# City in parens: must start uppercase, ≥ 3 chars, allow slash for "Drunen/Waalwijk"
_CITY_PAREN_RE = re.compile(r"\(([A-Z][A-Za-zÀ-ÿ\s\-\/]{2,30}?)\)")
_HOURS_LABEL_RE = re.compile(r"uren?\s+per\s+week", re.I)
# Known Mikz service area cities (Noord-Brabant)
_MIKZ_CITIES = {"waalwijk", "drunen", "vlijmen", "heusden", "loon op zand",
                "kaatsheuvel", "sprang-capelle", "waspik"}


class MikzScraper(WordPressJobsScraper):
    company_slug     = "mikz"
    company_name     = "Mikz"
    listing_url      = "https://www.mikz.nl/werkenenlerenbij/"
    website_url      = "https://www.mikz.nl"
    job_url_contains = "/werkenenlerenbij/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[mikz] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None
        # Filter out the listing page itself and generic non-job pages
        if title.lower() in {"onze vacatures", "vacatures"}:
            return None

        # City: first try parentheses anywhere in title, e.g. "BSO (Waalwijk) i.c.m."
        # For "Drunen/Waalwijk" take only the first city before the slash.
        city = ""
        m = _CITY_PAREN_RE.search(title)
        if m:
            city = m.group(1).split("/")[0].strip()
        else:
            # Fallback: last word if it's a known Mikz service area city
            words = title.split()
            if words and words[-1].lower() in _MIKZ_CITIES:
                city = words[-1]
            elif len(words) >= 2 and " ".join(words[-2:]).lower() in _MIKZ_CITIES:
                city = " ".join(words[-2:])

        # Hours: look for "Uren per week" label in sidebar blocks
        hours_min = hours_max = None
        for gamma in soup.select(".block--brand-sec div.gamma"):
            text = gamma.get_text(strip=True)
            if _HOURS_LABEL_RE.search(text):
                hours_min, hours_max = _parse_hours(text)
                if hours_min is None:
                    # e.g. "Uren per week : 20"
                    nm = re.search(r":\s*(\d+)", text)
                    if nm:
                        hours_min = hours_max = int(nm.group(1))
                break

        # Description: intro paragraph + content block
        desc_parts = []
        intro_el = soup.select_one(".intro")
        if intro_el:
            desc_parts.append(intro_el.get_text(separator="\n", strip=True))
        content_el = soup.select_one(".content")
        if content_el:
            desc_parts.append(content_el.get_text(separator="\n", strip=True))
        if not desc_parts:
            body = soup.find("body")
            desc_parts.append(body.get_text(separator="\n", strip=True)[:5000] if body else "")
        desc = "\n\n".join(desc_parts)[:5000]

        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     city,
            "city":              city,
            "street":            "",
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
