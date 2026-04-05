"""
Forte Kinderopvang — werkenbijforte.nl

Platform: WordPress REST API (/wp-json/wp/v2/vacature)
Meta-velden per item:
  vacatures_locatie         → plaatsnaam (stad)
  vacatures_locatie2        → locatienaam (bijv. "BSO De Speelhut")
  vacatures_werkelijkeuren  → leesbare uren string (bijv. "22-30 uur")
"""

import logging
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressRestApiScraper, _parse_hours, _strip_html

logger = logging.getLogger(__name__)


class ForteScraper(WordPressRestApiScraper):
    company_slug      = "forte"
    company_name      = "Forte Kinderopvang"
    website_url       = "https://werkenbijforte.nl"
    wp_rest_post_type = "vacature"

    def fetch_jobs(self) -> list[dict]:
        base = f"{self.website_url}/wp-json/wp/v2/{self.wp_rest_post_type}"
        jobs = []
        page = 1
        while True:
            try:
                resp = requests.get(
                    base,
                    params={"per_page": 100, "page": page, "status": "publish"},
                    headers=SCRAPER_HEADERS,
                    timeout=20,
                )
                if resp.status_code == 400:
                    break
                resp.raise_for_status()
                items = resp.json()
                if not items:
                    break

                for item in items:
                    job = self._item_to_job(item)
                    if job:
                        jobs.append(job)

                if len(items) < 100:
                    break
                page += 1
                time.sleep(0.3)
            except Exception as exc:
                logger.warning(f"[forte] REST API p{page} mislukt: {exc}")
                break

        logger.info(f"[forte] {len(jobs)} vacatures gescraped")
        return jobs

    def _item_to_job(self, item: dict) -> dict | None:
        title = (item.get("title") or {}).get("rendered", "").strip()
        if not title:
            return None

        link = item.get("link", "")
        meta = item.get("meta") or {}

        city          = (meta.get("vacatures_locatie") or "").strip()
        location2     = (meta.get("vacatures_locatie2") or "").strip()
        location_name = f"{location2}, {city}".strip(", ") if location2 else city

        uren_text = (meta.get("vacatures_werkelijkeuren") or "").strip()
        hours_min, hours_max = _parse_hours(uren_text)

        desc_raw = (item.get("content") or {}).get("rendered", "")
        desc = _strip_html(desc_raw) if desc_raw else ""

        if hours_min is None:
            hours_min, hours_max = _parse_hours(desc)

        external_id = str(item.get("id", "")) or link.rstrip("/").split("/")[-1]

        return {
            "source_url":        link,
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
