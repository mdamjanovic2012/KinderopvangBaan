"""
Prokino scraper — werkenbij.prokino.nl

Platform: AFAS OutSite (Anta CMS) with JavaScript rendering.
Requires Playwright.

Structure:
  - Category pages: /vacatures-kinderopvang, /vacatures-bso, /vacatures-peuteropvang,
    /vacatures-centraal-bureau, /vacatures-meander
  - Job cards: a.vtlink with span.text elements: [title, hours, city, status, deadline]
  - Detail pages: /{category}/{slug} — full description in sections
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://werkenbij.prokino.nl"

# Category listing pages to scrape
CATEGORY_PAGES = [
    f"{BASE_URL}/vacatures-kinderopvang",
    f"{BASE_URL}/vacatures-bso",
    f"{BASE_URL}/vacatures-peuteropvang",
    f"{BASE_URL}/vacatures-centraal-bureau",
    f"{BASE_URL}/vacatures-meander",
]

# Job URL path prefixes (category slugs used in job URLs)
JOB_PATH_PREFIXES = (
    "/kinderopvang/",
    "/bso/",
    "/peuteropvang/",
    "/centraal-bureau/",
    "/meander/",
)

SALARY_RE   = re.compile(r"€\s*([\d.,]+)\s*[-–]\s*€?\s*([\d.,]+)", re.I)
HOURS_RE    = re.compile(r"(\d+)\s*(?:tot|[-–])\s*(\d+)\s*uur", re.I)
POSTCODE_RE = re.compile(r"(\d{4}\s*[A-Z]{2})")
STREET_RE   = re.compile(
    r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-\.]{3,50}?)\s+(\d{1,4}[a-zA-Z]{0,2})"
    r"(?=\s*[,\n]?\s*\d{4}\s*[A-Z]{2})",
    re.I,
)


def _parse_euros(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def _render_page(context: BrowserContext, url: str) -> str:  # pragma: no cover
    """Render a page with Playwright and return full HTML."""
    page = context.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2_000)
        return page.content()
    except PlaywrightTimeout:
        logger.warning(f"[prokino] Timeout rendering {url}")
        return ""
    finally:
        page.close()


def _extract_cards_from_listing(html: str, seen_urls: set) -> list[dict]:
    """
    Parse job cards from a Prokino category listing page.
    Cards are a.vtlink elements with span.text children:
      [0] title, [1] hours (float), [2] city, [3] status ('open'/'vervuld'), [4] deadline
    Only includes open vacancies.
    """
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for a in soup.select("a.vtlink[href]"):
        href = a.get("href", "")
        if not any(href.startswith(prefix) for prefix in JOB_PATH_PREFIXES):
            continue

        url = BASE_URL + href
        if url in seen_urls:
            continue

        spans = [s.get_text(strip=True) for s in a.select("span.text") if s.get_text(strip=True)]
        if len(spans) < 3:
            continue

        title  = spans[0] if len(spans) > 0 else ""
        hours_raw = spans[1] if len(spans) > 1 else ""
        city   = spans[2] if len(spans) > 2 else ""
        status = spans[3].lower() if len(spans) > 3 else "open"

        if status == "vervuld":
            continue  # Skip filled vacancies

        # Hours: "24,00" → float → int
        hours_min = hours_max = None
        try:
            h = float(hours_raw.replace(",", "."))
            if h > 0:
                hours_min = hours_max = int(h)
        except ValueError:
            pass

        external_id = href.rstrip("/").split("/")[-1]
        seen_urls.add(url)

        jobs.append({
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": "",
            "description":       "",
            "location_name":     city,
            "city":              city,
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

    return jobs


def _enrich_from_detail(html: str, job: dict) -> None:
    """Parse detail page HTML and enrich job with description, salary, and refined hours."""
    if not html:
        return
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup.find("article") or soup
    text = main.get_text(separator="\n", strip=True)

    # Description from all h2 sections
    job["description"] = text[:5000]
    job["short_description"] = text[:300]

    # Salary from body text: "€2.641 – €3.630"
    m = SALARY_RE.search(text)
    if m:
        job["salary_min"] = _parse_euros(m.group(1))
        job["salary_max"] = _parse_euros(m.group(2))

    # Hours range from body: "16 tot 24 uur per week"
    m = HOURS_RE.search(text)
    if m:
        job["hours_min"] = int(m.group(1))
        job["hours_max"] = int(m.group(2))

    # Address: postcode + optionally street before it
    pc_m = POSTCODE_RE.search(text)
    if pc_m:
        postcode = pc_m.group(1).replace(" ", "")
        city = job.get("city", "")
        before = text[max(0, pc_m.start() - 100):pc_m.start()]
        st_m = STREET_RE.search(before + " " + pc_m.group(1))
        if st_m:
            street = f"{st_m.group(1).strip()} {st_m.group(2).strip()}"
            job["location_name"] = f"{street}, {postcode} {city}".strip(", ").strip()
        elif city:
            job["location_name"] = f"{postcode} {city}"
        else:
            job["location_name"] = postcode
        job["postcode"] = postcode


class ProkinoScraper(BaseScraper):
    company_slug = "prokino"

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
            logger.warning(f"[prokino] Company info failed: {exc}")

        return {
            "name":          "Prokino",
            "website":       BASE_URL,
            "job_board_url": f"{BASE_URL}/vacatures-kinderopvang",
            "scraper_class": "ProkinoScraper",
            "logo_url":      logo_url,
            "description":   description,
        }

    def fetch_jobs(self) -> list[dict]:
        logger.info(f"[prokino] Starting Playwright scrape")

        with sync_playwright() as pw:  # pragma: no cover
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=SCRAPER_HEADERS["User-Agent"],
                locale="nl-NL",
            )

            try:
                seen_urls: set[str] = set()
                all_jobs: list[dict] = []

                # Collect cards from all category pages
                for cat_url in CATEGORY_PAGES:
                    logger.info(f"[prokino] Category: {cat_url}")
                    try:
                        html = _render_page(context, cat_url)
                        cards = _extract_cards_from_listing(html, seen_urls)
                        all_jobs.extend(cards)
                        logger.info(f"[prokino] {len(cards)} vacatures from {cat_url}")
                    except Exception as exc:
                        logger.warning(f"[prokino] Category page failed {cat_url}: {exc}")
                    time.sleep(0.5)

                logger.info(f"[prokino] Total unique vacatures: {len(all_jobs)}")

                # Enrich each job with detail page data
                for job in all_jobs:
                    try:
                        detail_html = _render_page(context, job["source_url"])
                        _enrich_from_detail(detail_html, job)
                        time.sleep(0.5)
                    except Exception as exc:
                        logger.warning(f"[prokino] Detail page failed {job['source_url']}: {exc}")

            finally:
                context.close()
                browser.close()

        return all_jobs
