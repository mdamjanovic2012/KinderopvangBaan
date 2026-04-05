"""
Kinderopvang Walcheren scraper — werkenbijkow.nl

Platform: WordPress. No JSON-LD.
Job links use protocol-relative URLs (//www.werkenbijkow.nl/vacatures/{slug}).
Custom _get_all_job_urls to handle // prefix.
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours
from scrapers.base import SCRAPER_HEADERS

_IN_CITY_RE = re.compile(r"\b(?:in|te)\s+([A-Z][A-Za-zÀ-ÿ\-]{2,25})", re.I)
_POSTCODE_CITY_RE = re.compile(r"\d{4}\s*[A-Z]{2}\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s]{1,25}?)(?:\s*[,\n]|$)")

logger = logging.getLogger(__name__)

BASE_URL  = "https://www.werkenbijkow.nl"
JOBS_URL  = f"{BASE_URL}/vacatures/"


class KOWalcherenScraper(WordPressJobsScraper):
    company_slug     = "ko-walcheren"
    company_name     = "Kinderopvang Walcheren"
    listing_url      = JOBS_URL
    website_url      = BASE_URL
    job_url_contains = "/vacatures/"

    def _get_all_job_urls(self) -> list[str]:
        """Override to handle protocol-relative URLs (//www.werkenbijkow.nl/...)."""
        try:
            resp = requests.get(self.listing_url, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[ko-walcheren] Listing failed: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Resolve protocol-relative URLs
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = BASE_URL + href

            if self.job_url_contains not in href:
                continue

            path = href.replace(BASE_URL, "")
            segments = [s for s in path.strip("/").split("/") if s]
            if len(segments) >= 2 and href not in seen:
                seen.add(href)
                links.append(href)

        logger.info(f"[ko-walcheren] {len(links)} job URLs found")
        return links

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[ko-walcheren] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Title: h1 says "KOW zoekt jou!" — real title is in h4 below it
        h1 = soup.find("h1")
        title = ""
        if h1:
            h4 = h1.find_next("h4")
            if h4:
                title = h4.get_text(strip=True)
        if not title:
            heading = soup.find("h1") or soup.find("h2")
            title = heading.get_text(strip=True) if heading else ""
        if not title:
            return None

        # Specificaties sidebar: find h5 labels → next p values
        location_name = city = ""
        hours_min = hours_max = None

        for inner in soup.select(".et_pb_text_inner"):
            h5 = inner.find("h5")
            if not h5:
                continue
            label = h5.get_text(strip=True)
            p = inner.find("p")
            if not p:
                continue
            value = p.get_text(strip=True)
            if "Locatie" in label or "locatie" in label:
                location_name = value
                # Extract city: "BSO Koraal in Vlissingen" → "Vlissingen"
                m = _IN_CITY_RE.search(value)
                if m:
                    city = m.group(1)
                else:
                    m = _POSTCODE_CITY_RE.search(value)
                    if m:
                        city = m.group(1).strip()
                    else:
                        # Last capitalized word as fallback
                        words = value.split()
                        for w in reversed(words):
                            w = w.strip(".,:")
                            if w and w[0].isupper() and len(w) >= 3 and not w.isupper():
                                city = w
                                break
            elif "uur" in label.lower():
                hours_min, hours_max = _parse_hours(value)

        # Description from main content
        main = soup.select_one("main") or soup.select_one("article") or soup.select_one(".et_pb_section")
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
            "location_name":     location_name,
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
