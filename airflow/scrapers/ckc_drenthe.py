"""
CKC Drenthe scraper — www.werkenbijckcdrenthe.nl

Platform: GetNoticed CMS (Symfony) — vacatures worden client-side geladen via JavaScript.
Playwright renderen de listing; detail-pagina's worden met requests + BeautifulSoup geparsed.
JSON-LD wordt als primaire bron gebruikt; HTML is fallback.

Listing URL: https://www.werkenbijckcdrenthe.nl/vacatures?_locale=nl
Job URL pattern: https://www.werkenbijckcdrenthe.nl/vacature/{slug}
"""

import logging
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS
from scrapers.wordpress_jobs import (
    extract_job_posting_jsonld,
    parse_job_from_jsonld,
    _parse_hours,
)

logger = logging.getLogger(__name__)

BASE_URL  = "https://www.werkenbijckcdrenthe.nl"
JOBS_URL  = f"{BASE_URL}/vacatures?_locale=nl"


def _get_job_urls_playwright() -> list[str]:  # pragma: no cover
    """Render listing page with Playwright and extract job detail URLs."""
    try:
        from playwright.sync_api import sync_playwright
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
    except ImportError:
        logger.warning("[ckc-drenthe] Playwright niet geïnstalleerd — geen vacatures opgehaald")
        return []

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
                logger.warning("[ckc-drenthe] Timeout bij het renderen van de listing pagina")
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
            # Match /vacature/{slug} (singular, not /vacatures/)
            if "/vacature/" in href and not href.rstrip("/").endswith("/vacature"):
                if href.startswith("http"):
                    url = href
                else:
                    url = BASE_URL + href
                # Normalize: strip query strings from job URLs
                url = url.split("?")[0]
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
    except Exception as exc:
        logger.warning(f"[ckc-drenthe] Playwright listing mislukt: {exc}")

    logger.info(f"[ckc-drenthe] {len(urls)} vacature-URLs gevonden via listing")
    return urls


class CKCDrentheScraper(BaseScraper):
    company_slug = "ckc-drenthe"

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
            logger.warning(f"[ckc-drenthe] Bedrijfsinfo ophalen mislukt: {exc}")

        return {
            "name":          "CKC Drenthe",
            "website":       BASE_URL,
            "job_board_url": JOBS_URL,
            "scraper_class": "CKCDrentheScraper",
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

                # Probeer JSON-LD eerst
                jsonld = extract_job_posting_jsonld(soup)
                if jsonld and jsonld.get("title"):
                    job = parse_job_from_jsonld(url, jsonld)
                    jobs.append(job)
                    continue

                # HTML fallback
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else ""
                if not title:
                    logger.debug(f"[ckc-drenthe] Geen titel gevonden op {url} — overgeslagen")
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
                logger.warning(f"[ckc-drenthe] Detail pagina mislukt {url}: {exc}")

        logger.info(f"[ckc-drenthe] {len(jobs)} vacatures gescrapet")
        return jobs
