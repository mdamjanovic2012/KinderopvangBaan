"""
Kibeo scraper — werkenbijkibeo.nl

Covers Kibeo, WiedeWei, Elorah, Junia and Kindontwikkeling Kik
(all hosted on werkenbijkibeo.nl).

Platform: Custom site behind Cloudflare — requires Playwright for JS execution.

Approach:
  1. Render listing page via Playwright (bypasses Cloudflare JS challenge)
  2. Extract job links from rendered HTML
  3. Scrape each detail page via Playwright
  4. Extract JobPosting JSON-LD or fall back to HTML parsing
"""

import logging
import time

from playwright.sync_api import sync_playwright, BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS
from scrapers.wordpress_jobs import (
    extract_job_posting_jsonld,
    parse_job_from_jsonld,
    get_job_links_from_listing,
    _parse_hours,
)

logger = logging.getLogger(__name__)

BASE_URL  = "https://www.werkenbijkibeo.nl"
JOBS_URL  = f"{BASE_URL}/vacatures/"
JUNIA_URL = f"{BASE_URL}/werken-bij-junia/"


def _render_page(context: BrowserContext, url: str, wait_ms: int = 3000) -> str:
    """Render a page via Playwright and return full HTML."""
    page = context.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(wait_ms)
        return page.content()
    except PlaywrightTimeout:
        logger.warning(f"[kibeo] Timeout rendering {url}")
        return page.content()
    finally:
        page.close()


def _scrape_detail_html(context: BrowserContext, url: str) -> dict | None:
    """Scrape a single job detail page. Returns job dict or None."""
    html = _render_page(context, url, wait_ms=1500)
    soup = BeautifulSoup(html, "lxml")

    # Try JSON-LD first
    jsonld = extract_job_posting_jsonld(soup)
    if jsonld and jsonld.get("title"):
        return parse_job_from_jsonld(url, jsonld)

    # HTML fallback
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    if not title:
        return None

    main = (
        soup.select_one(".job-description")
        or soup.select_one("article")
        or soup.select_one("main")
    )
    desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
    hours_min, hours_max = _parse_hours(desc)
    external_id = url.rstrip("/").split("/")[-1]

    return {
        "source_url":        url,
        "external_id":       external_id,
        "title":             title,
        "short_description": desc[:300],
        "description":       desc,
        "location_name":     "",
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


class KibeoScraper(BaseScraper):
    company_slug = "kibeo"

    def fetch_company(self) -> dict:
        return {
            "name":          "Kibeo",
            "website":       BASE_URL,
            "job_board_url": JOBS_URL,
            "scraper_class": "KibeoScraper",
            "logo_url":      "",
            "description":   "Kibeo, WiedeWei, Elorah, Junia en Kindontwikkeling Kik",
        }

    def fetch_jobs(self) -> list[dict]:
        logger.info(f"[kibeo] Start Playwright scraping: {JOBS_URL}")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=SCRAPER_HEADERS["User-Agent"],
                locale="nl-NL",
            )
            try:
                # Collect job URLs from all listing pages
                all_urls: set[str] = set()
                for listing_url in [JOBS_URL, JUNIA_URL]:
                    html = _render_page(context, listing_url)
                    links = get_job_links_from_listing(html, BASE_URL, "/vacatures/")
                    # Also look for /werken-bij-*/vacature/ patterns
                    links += get_job_links_from_listing(html, BASE_URL, "/werken-bij-")
                    all_urls.update(links)
                    logger.info(f"[kibeo] {len(links)} links from {listing_url}")
                    time.sleep(0.5)

                logger.info(f"[kibeo] Total {len(all_urls)} unique job URLs")

                jobs = []
                for url in all_urls:
                    job = _scrape_detail_html(context, url)
                    if job:
                        jobs.append(job)
                    time.sleep(0.5)

            finally:
                context.close()
                browser.close()

        logger.info(f"[kibeo] Scraped {len(jobs)} vacatures")
        return jobs
