"""
Kindergarden scraper — werkenbijkindergarden.nl

Platform: Custom CMS with JavaScript-rendered listing.
Listing requires Playwright; detail pages serve JSON-LD without JS.
URL pattern: /vacatures/{slug}-{id}
"""

import logging
import time

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from scrapers.base import BaseScraper, SCRAPER_HEADERS
from scrapers.wordpress_jobs import (
    extract_job_posting_jsonld,
    parse_job_from_jsonld,
    _parse_hours,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.werkenbijkindergarden.nl"
JOBS_URL = f"{BASE_URL}/vacatures/"


def _get_job_urls_playwright() -> list[str]:
    """Render listing page with Playwright and extract job URLs."""
    urls = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=SCRAPER_HEADERS["User-Agent"],
                locale="nl-NL",
            )
            page = ctx.new_page()
            try:
                page.goto(JOBS_URL, wait_until="networkidle", timeout=60_000)
                page.wait_for_timeout(3_000)
                html = page.content()
            except PlaywrightTimeout:
                logger.warning("[kindergarden] Timeout rendering listing page")
                html = ""
            finally:
                ctx.close()
                browser.close()

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if href.startswith("/vacatures/") and "-" in href and href != "/vacatures/":
                url = BASE_URL + href
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
    except Exception as exc:
        logger.warning(f"[kindergarden] Playwright listing failed: {exc}")

    logger.info(f"[kindergarden] {len(urls)} job URLs from listing")
    return urls


class KindergardenScraper(BaseScraper):
    company_slug = "kindergarden"

    def fetch_company(self) -> dict:
        logo_url = description = ""
        try:
            resp = requests.get(BASE_URL, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for sel in ["header img[src]", ".logo img[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    if src.startswith("data:"):
                        continue
                    logo_url = src if src.startswith("http") else BASE_URL + src
                    if len(logo_url) > 199:
                        logo_url = ""
                    break
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")
        except Exception as exc:
            logger.warning(f"[kindergarden] Company info failed: {exc}")

        return {
            "name":          "Kindergarden",
            "website":       BASE_URL,
            "job_board_url": JOBS_URL,
            "scraper_class": "KindergardenScraper",
            "logo_url":      logo_url,
            "description":   description,
        }

    def fetch_jobs(self) -> list[dict]:
        job_urls = _get_job_urls_playwright()
        if not job_urls:
            return []

        jobs = []
        for url in job_urls:
            try:
                resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                jsonld = extract_job_posting_jsonld(soup)
                if jsonld and jsonld.get("title"):
                    job = parse_job_from_jsonld(url, jsonld)
                    jobs.append(job)
                    continue

                # HTML fallback
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else ""
                if not title:
                    continue

                main = soup.select_one("main") or soup.select_one("article") or soup
                desc = main.get_text(separator="\n", strip=True)[:5000]
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
                    "postcode":          "",
                    "salary_min":        None,
                    "salary_max":        None,
                    "hours_min":         hours_min,
                    "hours_max":         hours_max,
                    "age_min":           None,
                    "age_max":           None,
                    "contract_type":     "",
                    "job_type":          "",
                })
                time.sleep(0.3)
            except Exception as exc:
                logger.warning(f"[kindergarden] Detail page failed {url}: {exc}")

        logger.info(f"[kindergarden] {len(jobs)} vacatures scraped")
        return jobs
