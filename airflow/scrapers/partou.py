"""
Partou scraper — werkenbijpartou.nl

Partou gebruikt Contentful als headless CMS.
Vacatures worden opgehaald via de Contentful GraphQL API.

Geen Playwright nodig: directe HTTP-calls naar de Contentful API.
"""

import logging
import re

import requests

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL  = "https://www.werkenbijpartou.nl"
JOBS_URL  = f"{BASE_URL}/vacatures"

CONTENTFUL_ENDPOINT = (
    "https://graphql.contentful.com/content/v1/spaces/xbegxinjalez"
    "/environments/release-v2-2023"
)
CONTENTFUL_TOKEN = "uX1ZnOM4d0UTKo8pOhhELfrbBvyuPDbRcY0rdXvPDCE"

CONTENTFUL_QUERY = """
{
  vacancyCollection(limit: 1000, skip: 0) {
    total
    items {
      sys { id }
      roleTitle
      role
      city
      slug
      minHours
      maxHours
      minSalary
      maxSalary
      numberOfHours
      childcareType
      aboutJob
      headerText
      link
      vacancyId
    }
  }
}
"""

SALARY_RE = re.compile(r"€\s*([\d.,]+)\s*[-–]\s*€?\s*([\d.,]+)", re.I)
HOURS_RE  = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*uur", re.I)

# Facility type prefixes that appear between "|" and the actual location name
# in Partou job titles, e.g. "Pedagogisch Medewerker | BSO Bolstraat Amsterdam"
_FACILITY_PREFIXES = [
    "KDV VE en BSO", "KDV en BSO", "KDV VE", "Sport BSO", "Flex VE",
    "BBL-opleiding", "EVC Traject", "POV VE", "Flexpool Regio",
    "Verticale groep", "Babygroep", "Peutergroep", "Flexpool",
    "BBL", "EVC", "KDV", "BSO", "POV", "VE", "IKC",
]
_PARTOU_TYPE_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(re.escape(p) for p in _FACILITY_PREFIXES) + r")\s+",
    re.IGNORECASE,
)


def _extract_location_from_title(title: str, city: str) -> str:
    """
    Extract a precise location string from a Partou job title.

    Partou titles often encode the specific branch location:
      "Pedagogisch Medewerker | BSO Bolstraat Utrecht" + city="Utrecht"
      → "Bolstraat, Utrecht"
      "Pedagogisch Medewerker | Babygroep Amsterdam West" + city="Amsterdam"
      → "Amsterdam West"  (district is better than bare city)

    Falls back to city when no specific location can be extracted.
    """
    if not city:
        return city or ""
    if "|" not in title:
        return city

    # Part after first pipe; drop any further pipe-separated segments
    part = title.split("|", 1)[1].strip().split("|")[0].strip()

    # Strip facility/role type prefix
    part = _PARTOU_TYPE_PREFIX_RE.sub("", part).strip()

    if not part:
        return city

    # If part already starts with the city name, it's a city-district descriptor
    # like "Amsterdam West" or "Amsterdam-Zuid" — use as-is for better geocoding
    if part.lower().startswith(city.lower()):
        return part.strip()

    # Otherwise try to strip the city name from the end to isolate the street
    city_end_re = re.compile(
        r"[\s,\-]+?" + re.escape(city) + r"(?:\s*[\-\–/]\s*\w+)?\s*$",
        re.IGNORECASE,
    )
    street = city_end_re.sub("", part).strip().strip(",").strip()

    if len(street) > 2 and re.search(r"[A-Za-z]{2}", street):
        return f"{street}, {city}"

    # Part contained only the city or couldn't be parsed
    return part if re.search(r"[A-Za-z]", part) else city

CONTRACT_MAP = {
    "fulltime":  "fulltime",
    "full-time": "fulltime",
    "parttime":  "parttime",
    "part-time": "parttime",
    "tijdelijk": "temp",
}

# Contentful role → interne job_type
ROLE_MAP = {
    "pedagogical":   "",          # verfijnd via childcareType hieronder
    "locationManager": "locatiemanager",
    "groupsHelp":    "groepshulp",
    "internship":    "stage",
    "facility":      "facilitair",
    "it":            "",
    "finance":       "",
    "hr":            "",
}

CHILDCARE_JOB_MAP = {
    "kdv":                "pm3",
    "bso":                "bso_begeleider",
    "combi kdv / bso":    "pm3",
    "pov":                "pm_pov",
    "combi pov / bso":    "pm_pov",
}


def _parse_euros(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def _parse_contract(raw: str) -> str:
    for key, val in CONTRACT_MAP.items():
        if key in raw.lower():
            return val
    return ""


def _job_type_from_role(role: str, childcare_type: str) -> str:
    if role == "pedagogical":
        return CHILDCARE_JOB_MAP.get((childcare_type or "").lower(), "")
    return ROLE_MAP.get(role, "")


def _parse_json_items(items: list) -> list[dict]:
    """
    Parseer ruwe JSON items (voor unit tests en als fallback).
    Verwacht velden: id, title, url/link/applyUrl, location, hours, salary,
    summary, description, contractType.
    """
    jobs = []
    for item in items:
        url = item.get("url") or item.get("link") or item.get("applyUrl", "")
        if not url or not url.startswith("http"):
            url = BASE_URL + url if url else ""
        if not url:
            continue

        title     = item.get("title") or item.get("name", "")
        location  = item.get("location") or item.get("city") or item.get("vestiging", "")
        hours_text = str(item.get("hours") or item.get("uren", ""))
        salary_text = str(item.get("salary") or item.get("salaris", ""))

        hours_min = hours_max = None
        m = HOURS_RE.search(hours_text)
        if m:
            hours_min, hours_max = int(m.group(1)), int(m.group(2))

        salary_min = salary_max = None
        m = SALARY_RE.search(salary_text)
        if m:
            salary_min = _parse_euros(m.group(1))
            salary_max = _parse_euros(m.group(2))

        jobs.append({
            "source_url":       url,
            "external_id":      str(item.get("id", "")),
            "title":            title,
            "short_description": item.get("summary") or item.get("intro", ""),
            "description":      item.get("description", ""),
            "location_name":    location,
            "hours_min":        hours_min,
            "hours_max":        hours_max,
            "salary_min":       salary_min,
            "salary_max":       salary_max,
            "age_min":          None,
            "age_max":          None,
            "contract_type":    _parse_contract(str(item.get("contractType", ""))),
            "job_type":         "",
        })
    return jobs


def _parse_contentful_items(items: list) -> list[dict]:
    """Parseer Contentful GraphQL response items naar job dicts."""
    jobs = []
    for item in items:
        slug  = item.get("slug") or ""
        link  = item.get("link") or ""
        title = item.get("roleTitle") or ""
        if not title:
            continue

        if link and link.startswith("http"):
            source_url = link
        elif slug:
            source_url = f"{JOBS_URL}/{slug}"
        else:
            continue

        hours_min = item.get("minHours") or None
        hours_max = item.get("maxHours") or None
        # 0 betekent onbekend in de API
        if hours_min == 0:
            hours_min = None
        if hours_max == 0:
            hours_max = None

        salary_min = item.get("minSalary") or None
        salary_max = item.get("maxSalary") or None

        role         = item.get("role") or ""
        childcare    = item.get("childcareType") or ""
        job_type     = _job_type_from_role(role, childcare)
        external_id  = str(item.get("vacancyId") or item.get("sys", {}).get("id", ""))
        description  = item.get("aboutJob") or ""
        short_desc   = item.get("headerText") or ""

        city = item.get("city") or ""
        jobs.append({
            "source_url":        source_url,
            "external_id":       external_id,
            "title":             title,
            "short_description": short_desc[:500] if short_desc else "",
            "description":       description,
            "location_name":     _extract_location_from_title(title, city),
            "city":              city,
            "postcode":          "",
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "salary_min":        float(salary_min) if salary_min else None,
            "salary_max":        float(salary_max) if salary_max else None,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          job_type,
        })
    return jobs


def _fetch_contentful() -> list[dict]:
    """Haal alle vacatures op via Contentful GraphQL API."""
    headers = {
        "Authorization": f"Bearer {CONTENTFUL_TOKEN}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        CONTENTFUL_ENDPOINT,
        json={"query": CONTENTFUL_QUERY},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    errors = data.get("errors")
    if errors:
        raise ValueError(f"Contentful API fout: {errors}")

    collection = data["data"]["vacancyCollection"]
    items = collection["items"]
    total = collection["total"]
    logger.info(f"[partou] Contentful: {len(items)} van {total} vacatures opgehaald")

    return _parse_contentful_items(items)


class PartouScraper(BaseScraper):
    company_slug = "partou"

    def fetch_company(self) -> dict:
        partou_home = "https://www.partou.nl"
        logo_url = ""
        description = ""
        try:
            from bs4 import BeautifulSoup
            resp = requests.get(partou_home, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            for sel in ["header img[src]", ".logo img[src]", "img.logo[src]", "img[alt*='partou' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    logo_url = src if src.startswith("http") else partou_home + src
                    break

            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")

        except Exception as exc:
            logger.warning(f"[partou] Bedrijfsinfo ophalen mislukt: {exc}")

        return {
            "name":          "Partou",
            "website":       partou_home,
            "job_board_url": JOBS_URL,
            "scraper_class": "PartouScraper",
            "logo_url":      logo_url,
            "description":   description,
        }

    def fetch_jobs(self) -> list[dict]:
        return _fetch_contentful()
