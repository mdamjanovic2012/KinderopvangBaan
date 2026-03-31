"""
TeamtailorRssScraper — basis voor Teamtailor career sites via RSS feed.

Teamtailor biedt een publiek RSS feed zonder API-sleutel:
  https://{career_site}/jobs.rss

RSS structuur (standaard RSS 2.0):
  <item>
    <title>   — vacaturetitel
    <link>    — detail URL (source_url)
    <guid>    — unieke ID (external_id)
    <description> — HTML omschrijving
    <pubDate> — publicatiedatum
    <category>— afdeling/department (optioneel, meerdere mogelijk)
  </item>

Subclass moet instellen:
  company_slug  — slug voor jobs_company tabel
  rss_url       — volledig RSS URL
  career_url    — hoofdpagina van de career site
  company_name  — officiële bedrijfsnaam

Optioneel te overriden:
  fetch_company() — voor logo/beschrijving van de website
"""

import logging
import re
import time
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

HOURS_RE    = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*uur", re.I)
SALARY_RE   = re.compile(r"€\s*([\d.,]+)\s*[-–]\s*€?\s*([\d.,]+)", re.I)
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


def _strip_html(html: str) -> str:
    """Verwijder HTML tags en geef platte tekst terug (max 5000 tekens)."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n", strip=True)[:5000]


def _parse_rss_items(xml_text: str) -> list[dict]:
    """
    Parseer RSS XML naar lijst van dicts met:
    title, link, guid, description_html, categories
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.error(f"RSS XML parse mislukt: {exc}")
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        guid  = (item.findtext("guid") or link).strip()
        desc  = (item.findtext("description") or "").strip()
        cats  = [c.text.strip() for c in item.findall("category") if c.text]
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "guid": guid,
                "description_html": desc,
                "categories": cats,
            })
    return items


def _fetch_detail_location(url: str) -> tuple[str, str, str]:
    """
    Fetch a Teamtailor job detail page and extract (city, postcode, location_name).
    Teamtailor pages have a location element and often contain structured address text.
    Returns ("", "", "") on failure.
    """
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Teamtailor location selectors (various versions)
        for sel in [
            "[data-qa='job-location']",
            ".job-meta__location",
            ".location",
            "[class*='location']",
            "span[itemprop='addressLocality']",
        ]:
            el = soup.select_one(sel)
            if el:
                loc_text = el.get_text(strip=True)
                if loc_text and len(loc_text) < 80:
                    return loc_text, "", loc_text

        # Fallback: scan full page text for postcode
        text = soup.get_text(separator=" ", strip=True)
        pc_m = POSTCODE_RE.search(text)
        if pc_m:
            postcode = pc_m.group(1).replace(" ", "")
            after = text[pc_m.end():pc_m.end() + 80]
            city_m = re.match(
                r"\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{1,40}?)(?:\s*[•·\n]|\s{2,}|\s+[A-Z][a-z]|\s*$)",
                after,
            )
            city = city_m.group(1).strip() if city_m else ""
            before = text[max(0, pc_m.start() - 120):pc_m.start()]
            st_m = STREET_RE.search(before + " " + pc_m.group(1))
            if st_m:
                street = f"{st_m.group(1).strip()} {st_m.group(2).strip()}"
                location_name = f"{street}, {postcode} {city}".strip(", ").strip()
            elif city:
                location_name = f"{postcode} {city}"
            else:
                location_name = postcode
            return city, postcode, location_name
    except Exception as exc:
        logger.warning(f"Detail location fetch failed {url}: {exc}")
    return "", "", ""


def _extract_job_fields(item: dict) -> dict:
    """
    Extraheer gestructureerde vacaturevelden uit een RSS item.
    Zoekt naar uren/salaris in de HTML-beschrijving.
    """
    desc_html = item["description_html"]
    desc_text = _strip_html(desc_html) if desc_html else ""

    hours_min = hours_max = None
    m = HOURS_RE.search(desc_text)
    if m:
        hours_min, hours_max = int(m.group(1)), int(m.group(2))

    salary_min = salary_max = None
    sm = SALARY_RE.search(desc_text)
    if sm:
        salary_min = _parse_euros(sm.group(1))
        salary_max = _parse_euros(sm.group(2))

    # Afdeling als job_type hint (eerste categorie)
    department = item["categories"][0] if item["categories"] else ""

    return {
        "source_url":        item["link"],
        "external_id":       item["guid"],
        "title":             item["title"],
        "short_description": desc_text[:300] if desc_text else "",
        "description":       desc_text,
        "location_name":     "",
        "city":              "",
        "postcode":          "",
        "salary_min":        salary_min,
        "salary_max":        salary_max,
        "hours_min":         hours_min,
        "hours_max":         hours_max,
        "age_min":           None,
        "age_max":           None,
        "contract_type":     "",
        "job_type":          "",
    }


class TeamtailorRssScraper(BaseScraper):
    """
    Basis Teamtailor RSS scraper.
    Subclass moet company_slug, rss_url, career_url en company_name instellen.
    """

    company_slug: str = ""
    rss_url:      str = ""
    career_url:   str = ""
    company_name: str = ""

    def fetch_company(self) -> dict:
        logo_url = description = ""
        try:
            resp = requests.get(self.career_url, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            for sel in ["header img[src]", ".logo img[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    logo_url = src if src.startswith("http") else self.career_url.rstrip("/") + src
                    break

            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Bedrijfsinfo ophalen mislukt: {exc}")

        return {
            "name":          self.company_name,
            "website":       self.career_url,
            "job_board_url": self.career_url,
            "scraper_class": self.__class__.__name__,
            "logo_url":      logo_url,
            "description":   description,
        }

    def fetch_jobs(self) -> list[dict]:
        logger.info(f"[{self.company_slug}] RSS ophalen: {self.rss_url}")
        try:
            resp = requests.get(self.rss_url, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"[{self.company_slug}] RSS ophalen mislukt: {exc}")
            return []

        items = _parse_rss_items(resp.text)
        logger.info(f"[{self.company_slug}] {len(items)} items in RSS feed")

        jobs = [_extract_job_fields(item) for item in items]

        # Enrich each job with location from detail page
        logger.info(f"[{self.company_slug}] Fetching detail pages voor locatie-informatie")
        for job in jobs:
            city, postcode, location_name = _fetch_detail_location(job["source_url"])
            if location_name:
                job["city"] = city
                job["location_name"] = location_name
                if postcode:
                    job["postcode"] = postcode
            time.sleep(0.3)

        return jobs
