"""
KomKids — werkenbij.komkids.nl (WordPress REST API: /wp-json/wp/v2/vacatures)

ACF fields used:
  vacature_werktijd: ["16-24 uur"] — hours
  vacature_plaats:   ["Schiedam West"] — area (first word = city)
  vacature_functie:  ["Pedagogisch Professional"] — job function
"""
import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import WordPressRestApiScraper, _parse_hours
from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)


class KomKidsScraper(WordPressRestApiScraper):
    company_slug      = "komkids"
    company_name      = "KomKids"
    website_url       = "https://werkenbij.komkids.nl"
    wp_rest_post_type = "vacatures"

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
            except Exception as exc:
                logger.warning(f"[komkids] REST API p{page} mislukt: {exc}")
                break

            for item in items:
                url = item.get("link", "")
                if not url:
                    continue

                title_raw = item.get("title", {}).get("rendered", "")
                title = BeautifulSoup(title_raw, "lxml").get_text(strip=True)
                if not title:
                    continue

                content_html = item.get("content", {}).get("rendered", "")
                desc = BeautifulSoup(content_html, "lxml").get_text(separator="\n", strip=True)[:5000]

                acf = item.get("acf", {}) or {}

                # Hours from vacature_werktijd e.g. ["16-24 uur"]
                werktijd = acf.get("vacature_werktijd") or []
                hours_min = hours_max = None
                for wt in (werktijd if isinstance(werktijd, list) else [werktijd]):
                    h_min, h_max = _parse_hours(str(wt))
                    if h_min:
                        hours_min, hours_max = h_min, h_max
                        break

                # City from vacature_plaats e.g. ["Schiedam West"] — first word is city
                plaats = acf.get("vacature_plaats") or []
                city = location_name = ""
                if isinstance(plaats, list) and plaats:
                    location_name = str(plaats[0]).strip()
                    city = location_name.split()[0] if location_name else ""
                elif isinstance(plaats, str) and plaats:
                    location_name = plaats.strip()
                    city = location_name.split()[0]

                external_id = url.rstrip("/").split("/")[-1]

                jobs.append({
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
                })

            if len(items) < 100:
                break
            page += 1

        logger.info(f"[komkids] {len(jobs)} vacatures via REST API")
        return jobs
