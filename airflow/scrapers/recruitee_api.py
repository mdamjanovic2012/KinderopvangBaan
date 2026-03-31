"""
RecruiteeAPIScraper — base class for companies using Recruitee ATS.

Recruitee provides a public JSON API at:
  https://api.recruitee.com/c/{company_id}/careers/offers?lang=nl

API fields used:
  title, city, postal_code, salary (min/max), min_hours_per_week,
  max_hours_per_week, description (HTML), careers_url, guid,
  employment_type_code, status

Only 'published' offers are included.
"""

import html
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

RECRUITEE_API = "https://api.recruitee.com/c/{company_id}/careers/offers?lang=nl"

EMPLOYMENT_TYPE_MAP = {
    "fulltime":  "fulltime",
    "parttime":  "parttime",
    "contract":  "temp",
    "temporary": "temp",
    "internship": "parttime",
    "freelance":  "temp",
}


def _strip_html(raw: str) -> str:
    """Strip HTML tags and decode entities."""
    soup = BeautifulSoup(raw, "lxml")
    return soup.get_text(separator="\n", strip=True)[:5000]


def _salary_val(raw) -> float | None:
    if raw is None:
        return None
    try:
        return float(str(raw).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


class RecruiteeAPIScraper(BaseScraper):
    company_slug:   str = ""
    company_name:   str = ""
    recruitee_id:   int = 0      # Recruitee company ID (integer)
    website_url:    str = ""
    job_board_url:  str = ""     # careers page URL shown to users

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
            "job_board_url": self.job_board_url or self.website_url,
            "scraper_class": self.__class__.__name__,
            "logo_url":      logo_url,
            "description":   description,
        }

    def fetch_jobs(self) -> list[dict]:
        api_url = RECRUITEE_API.format(company_id=self.recruitee_id)
        logger.info(f"[{self.company_slug}] Fetching from Recruitee API: {api_url}")

        try:
            resp = requests.get(api_url, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] API request failed: {exc}")
            return []

        offers = data.get("offers", [])
        logger.info(f"[{self.company_slug}] {len(offers)} offers from API")

        jobs = []
        for offer in offers:
            if offer.get("status") not in ("published", None, ""):
                continue

            title = offer.get("title", "").strip()
            if not title:
                continue

            city     = offer.get("city", "").strip()
            postcode = offer.get("postal_code", "").replace(" ", "").strip() if offer.get("postal_code") else ""

            salary   = offer.get("salary") or {}
            sal_min  = _salary_val(salary.get("min"))
            sal_max  = _salary_val(salary.get("max"))

            hours_min = offer.get("min_hours_per_week")
            hours_max = offer.get("max_hours_per_week") or offer.get("max_hours")
            if hours_min is not None:
                hours_min = int(hours_min)
            if hours_max is not None:
                hours_max = int(hours_max)

            desc_raw  = offer.get("description", "")
            desc      = _strip_html(desc_raw) if desc_raw else ""

            emp_code  = (offer.get("employment_type_code") or "").lower()
            contract  = EMPLOYMENT_TYPE_MAP.get(emp_code, "")

            source_url   = offer.get("careers_url", "")
            external_id  = str(offer.get("guid", offer.get("id", "")))
            if not external_id:
                external_id = source_url.rstrip("/").split("/")[-1]

            # Compose best location query for PDOK geocoding
            if postcode and city:
                location_name = f"{postcode} {city}"
            else:
                location_name = city

            jobs.append({
                "source_url":        source_url,
                "external_id":       external_id,
                "title":             title,
                "short_description": desc[:300],
                "description":       desc,
                "location_name":     location_name,
                "city":              city,
                "postcode":          postcode,
                "salary_min":        sal_min,
                "salary_max":        sal_max,
                "hours_min":         hours_min,
                "hours_max":         hours_max,
                "age_min":           None,
                "age_max":           None,
                "contract_type":     contract,
                "job_type":          "",
            })

        logger.info(f"[{self.company_slug}] {len(jobs)} vacatures processed")
        return jobs
