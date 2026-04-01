"""
Branch scraper — collects precise addresses of childcare company locations.

Problem: job listings only mention a city ("Rotterdam") but PDOK geocodes that
to the city centre. All Rotterdam vacancies end up with the same coordinates.

Solution: scrape the "branches/locations" page of the main company website
(NOT the job board), store name + full address in jobs_vestiging, and use
those precise coordinates as a fallback during job geocoding.

Table: jobs_vestiging is created by Django migration 0007_vestiging.
       The table name is kept as-is; the Django model is Branch.

Matching strategy:
  1. Exact name match: location_name == branch.name → precise coordinates
  2. City match (only if single branch in that city): city == branch.city
  3. Fallback: existing city-level geocoding (unchanged)

Supported companies:
  - Partou            (partou.nl/kinderopvang/vestigingen)
  - Kinderdam         (kinderdam.nl/locaties)
  - Spring            (spring-kinderopvang.nl/vestigingen)
  - Prokino           (prokino.nl)
  - Norlandia         (norlandia.nl/kinderopvang/vestigingen)
  - Gro-up            (gro-up.nl/locaties)
  - CompaNanny        (compananny.nl/vestigingen)
  - Sinne             (sinnekinderopvang.nl/vestigingen)
  - TintelTuin        (tinteltuin.nl/vestigingen)
  - Humankind         (humankind.nl/vestigingen)
  - Kibeo             (kibeo.nl/vestigingen)
  - Kindergarden      (kindergarden.nl/vestigingen)
  - Bijdehandjes      (bijdehandjes.nl/vestigingen)
  - Bink              (binkopvang.nl/vestigingen)
  - DAK               (dakkindercentra.nl/vestigingen)
  - Dichtbij          (kdv-dichtbij.nl/vestigingen)
  - Kinderwoud        (kinderwoud.nl/vestigingen)
  - Kids First        (kidsfirstkinderopvang.nl/vestigingen)
  - Kober             (kober.nl/vestigingen)
  - MIK               (mik-nijmegen.nl/vestigingen)
  - Op Stoom          (op-stoom.nl/vestigingen)
  - SKA               (ska.nl/vestigingen)
  - 2samen            (2samen.nl/vestigingen)
  - Wasko             (wasko.nl/vestigingen)
  - Wij zijn JONG     (korein.nl/vestigingen)
  - Kanteel           (kanteel.nl/vestigingen)
  - KO Walcheren      (kinderopvangwalcheren.nl/vestigingen)
  - Samenwerkende KO  (samenwerkendekinderopvang.nl/vestigingen)
  - KION              (kion.nl/vestigingen)
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS, _geocode_via_pdok
from db.connection import get_connection

logger = logging.getLogger(__name__)

# ── Regex helpers ─────────────────────────────────────────────────────────────

POSTCODE_RE = re.compile(r"(\d{4}\s*[A-Z]{2})")
STREET_RE = re.compile(
    r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-\.]{3,50}?)\s+(\d{1,4}[a-zA-Z]{0,2})"
    r"(?=\s*[,\n]?\s*\d{4}\s*[A-Z]{2})",
    re.I,
)


# ── DB helpers ────────────────────────────────────────────────────────────────

def upsert_vestiging(cur, company_slug: str, name: str, street: str,
                     postcode: str, city: str) -> None:
    """Upsert a branch record. Geocodes via PDOK if coordinates are missing."""
    # Build the best available geocoding query string
    query = ""
    if street and postcode and city:
        query = f"{street}, {postcode} {city}"
    elif postcode and city:
        query = f"{postcode} {city}"
    elif city:
        query = city

    lon = lat = None
    if query:
        geo = _geocode_via_pdok(query)
        if geo:
            lon = geo["lon"]
            lat = geo["lat"]
            if not city:
                city = geo.get("city", city)
            if not postcode:
                postcode = geo.get("postcode", postcode)

    if lon is not None:
        cur.execute("""
            INSERT INTO jobs_vestiging
                (company_slug, name, street, postcode, city, location, geocoded_at, updated_at)
            VALUES (%s, %s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    NOW(), NOW())
            ON CONFLICT (company_slug, name) DO UPDATE SET
                street      = EXCLUDED.street,
                postcode    = EXCLUDED.postcode,
                city        = EXCLUDED.city,
                location    = EXCLUDED.location,
                geocoded_at = EXCLUDED.geocoded_at,
                updated_at  = EXCLUDED.updated_at
        """, (company_slug, name, street, postcode, city, lon, lat))
    else:
        cur.execute("""
            INSERT INTO jobs_vestiging
                (company_slug, name, street, postcode, city, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (company_slug, name) DO UPDATE SET
                street     = EXCLUDED.street,
                postcode   = EXCLUDED.postcode,
                city       = EXCLUDED.city,
                updated_at = EXCLUDED.updated_at
        """, (company_slug, name, street, postcode, city))


def match_vestiging(cur, company_slug: str, location_name: str, city: str) -> dict | None:
    """
    Find precise branch coordinates for a job vacancy.
    Returns {lon, lat, postcode, city} or None.
    """
    # 1. Exact name match
    if location_name:
        cur.execute("""
            SELECT postcode, city,
                   ST_X(location::geometry) AS lon,
                   ST_Y(location::geometry) AS lat
            FROM jobs_vestiging
            WHERE company_slug = %s
              AND LOWER(TRIM(name)) = LOWER(TRIM(%s))
              AND location IS NOT NULL
        """, (company_slug, location_name))
        row = cur.fetchone()
        if row:
            return {"postcode": row[0], "city": row[1], "lon": row[2], "lat": row[3]}

        # Partial name match (branch name contains location_name or vice versa)
        cur.execute("""
            SELECT postcode, city,
                   ST_X(location::geometry) AS lon,
                   ST_Y(location::geometry) AS lat
            FROM jobs_vestiging
            WHERE company_slug = %s
              AND (LOWER(name) LIKE LOWER(%s) OR LOWER(%s) LIKE LOWER(CONCAT('%%', name, '%%')))
              AND location IS NOT NULL
            LIMIT 1
        """, (company_slug, f"%{location_name}%", location_name))
        row = cur.fetchone()
        if row:
            return {"postcode": row[0], "city": row[1], "lon": row[2], "lat": row[3]}

    # 2. City match — single branch: use exact coords; multiple: use centroid
    if city:
        cur.execute("""
            SELECT postcode, city,
                   ST_X(location::geometry) AS lon,
                   ST_Y(location::geometry) AS lat
            FROM jobs_vestiging
            WHERE company_slug = %s
              AND LOWER(TRIM(city)) = LOWER(TRIM(%s))
              AND location IS NOT NULL
        """, (company_slug, city))
        rows = cur.fetchall()
        if len(rows) == 1:
            return {"postcode": rows[0][0], "city": rows[0][1], "lon": rows[0][2], "lat": rows[0][3]}
        elif len(rows) > 1:
            # Multiple branches in city — use centroid so jobs spread out better
            # than pointing at the generic PDOK city centre
            avg_lon = sum(r[2] for r in rows) / len(rows)
            avg_lat = sum(r[3] for r in rows) / len(rows)
            return {"postcode": "", "city": rows[0][1], "lon": avg_lon, "lat": avg_lat}

    return None


# ── Generic address extraction ────────────────────────────────────────────────

def _extract_address_from_element(el) -> tuple[str, str, str]:
    """
    Try to extract name, street, and postcode+city from a BeautifulSoup element.
    Returns (name, street, postcode_city).
    """
    text = el.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return "", "", ""

    name = lines[0]
    street = postcode_city = ""

    for line in lines[1:]:
        pc_m = POSTCODE_RE.search(line)
        if pc_m and not postcode_city:
            postcode_city = line.strip()
        elif not street and len(line) > 3 and re.search(r"\d", line):
            street = line.strip()

    return name, street, postcode_city


def _parse_address_block(text: str) -> tuple[str, str, str]:
    """
    Parse an address from free text. Returns (street, postcode, city).
    """
    pc_m = POSTCODE_RE.search(text)
    if not pc_m:
        return "", "", ""

    postcode = pc_m.group(1).replace(" ", "")

    # City after postcode
    after = text[pc_m.end():pc_m.end() + 80]
    city_m = re.match(
        r"\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{1,40}?)(?:\s*[•·\n,]|\s{2,}|\s*$)",
        after,
    )
    city = city_m.group(1).strip() if city_m else ""

    # Street before postcode
    before = text[max(0, pc_m.start() - 120):pc_m.start()]
    st_m = STREET_RE.search(before + " " + pc_m.group(1))
    street = f"{st_m.group(1).strip()} {st_m.group(2).strip()}" if st_m else ""

    return street, postcode, city



# ── JavaScript data extraction helpers ───────────────────────────────────────

def _extract_js_json(html: str, var_name: str) -> list[dict]:
    """
    Extract a JSON array assigned to a JavaScript variable in a page.
    Handles: `var_name = [...]` and `var_name=[...]` patterns.
    """
    import json as _json
    pattern = re.compile(
        re.escape(var_name) + r"\s*=\s*(\[[\s\S]*?\])\s*;",
        re.DOTALL,
    )
    m = pattern.search(html)
    if not m:
        return []
    try:
        return _json.loads(m.group(1))
    except Exception:
        return []


# ── Company-specific scrapers ─────────────────────────────────────────────────

def scrape_partou_vestigingen() -> list[dict]:
    """
    Fetch all unique Partou facility addresses from the Contentful API.

    The vacancyCollection contains address, postalCode, city, and oeNumber
    (facility ID from the Dutch Care Registry). We deduplicate by oeNumber
    to get one entry per physical location (~378 unique facilities).
    """
    import json as _json
    from scrapers.partou import (
        CONTENTFUL_ENDPOINT, CONTENTFUL_TOKEN, CONTENTFUL_LOCATIONS_QUERY,
    )

    headers = {
        "Authorization": f"Bearer {CONTENTFUL_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(
            CONTENTFUL_ENDPOINT,
            json={"query": CONTENTFUL_LOCATIONS_QUERY},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error(f"[partou-branches] Contentful API failed: {exc}")
        return []

    items = data.get("data", {}).get("vacancyCollection", {}).get("items", [])

    # Deduplicate by oeNumber (facility ID); fall back to address string
    seen: dict[str, dict] = {}
    for item in items:
        address  = (item.get("address") or "").strip()
        postcode = (item.get("postalCode") or "").replace(" ", "").strip()
        city     = (item.get("city") or "").strip()
        oe       = str(item.get("oeNumber") or "")

        if not city or not (address or postcode):
            continue

        key = oe if oe else f"{address}|{postcode}|{city}"
        if key not in seen:
            # Name = address string (used for matching in match_vestiging)
            name = f"{address}, {city}" if address else f"{postcode} {city}"
            seen[key] = {
                "name":     name,
                "street":   address,
                "postcode": postcode,
                "city":     city,
            }

    locations = list(seen.values())
    logger.info(f"[partou-branches] {len(locations)} unique facilities from Contentful")
    return locations


def scrape_kinderdam_vestigingen() -> list[dict]:
    """
    Scrape Kinderdam branches from kinderdam.nl.
    """
    locations = []
    BASE = "https://www.kinderdam.nl"

    for path in ["/locaties", "/onze-locaties", "/vestigingen", "/over-kinderdam/locaties"]:
        url = BASE + path
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Schema.org JSON-LD
            for ld in soup.find_all("script", type="application/ld+json"):
                import json
                try:
                    data = json.loads(ld.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") in ("ChildCare", "LocalBusiness"):
                            addr = item.get("address", {})
                            name = item.get("name", "")
                            street = addr.get("streetAddress", "")
                            postcode = addr.get("postalCode", "").replace(" ", "")
                            city = addr.get("addressLocality", "")
                            if name and city:
                                locations.append({
                                    "name": name, "street": street,
                                    "postcode": postcode, "city": city,
                                })
                except Exception:
                    pass

            # HTML fallback: look for cards with name + address
            if not locations:
                for card in soup.select("article, [class*='location'], [class*='locatie'], .card"):
                    name_el = card.select_one("h2, h3, h4")
                    name = name_el.get_text(strip=True) if name_el else ""
                    text = card.get_text(separator="\n")
                    street, postcode, city = _parse_address_block(text)
                    if name and city:
                        locations.append({
                            "name": name, "street": street,
                            "postcode": postcode, "city": city,
                        })

            if locations:
                logger.info(f"[kinderdam-branches] {len(locations)} locations at {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[kinderdam-branches] {url} failed: {exc}")

    return locations


def _scrape_generic_vestigingen(company_slug: str, base_url: str,
                                 location_paths: list[str]) -> list[dict]:
    """
    Generic branch scraper for companies with a standard locations page.
    Tries schema.org JSON-LD first, then HTML cards.
    """
    import json
    locations = []

    for path in location_paths:
        url = base_url.rstrip("/") + path
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # JSON-LD structured data
            for ld in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(ld.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") in ("ChildCare", "LocalBusiness", "Organization"):
                            addr = item.get("address", {})
                            name = item.get("name", "")
                            street = addr.get("streetAddress", "")
                            postcode = addr.get("postalCode", "").replace(" ", "")
                            city = addr.get("addressLocality", "")
                            if name and city:
                                locations.append({
                                    "name": name, "street": street,
                                    "postcode": postcode, "city": city,
                                })
                except Exception:
                    pass

            # HTML card fallback
            if not locations:
                selectors = [
                    "[class*='location-card']", "[class*='vestiging']",
                    "[class*='locatie']", "article", ".card",
                ]
                for sel in selectors:
                    cards = soup.select(sel)
                    if not cards:
                        continue
                    for card in cards:
                        name_el = card.select_one("h2, h3, h4, strong")
                        name = name_el.get_text(strip=True) if name_el else ""
                        text = card.get_text(separator="\n")
                        street, postcode, city = _parse_address_block(text)
                        if name and city:
                            locations.append({
                                "name": name, "street": street,
                                "postcode": postcode, "city": city,
                            })
                    if locations:
                        break

            if locations:
                logger.info(f"[{company_slug}-branches] {len(locations)} locations at {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[{company_slug}-branches] {url} failed: {exc}")

    return locations


def scrape_compananny_vestigingen() -> list[dict]:
    """
    Scrape CompaNanny branches from compananny.com/locaties.
    The page embeds a JavaScript 'locations' array with address + zipcode per location.
    """
    locations = []
    for url in ["https://www.compananny.com/locaties", "https://www.compananny.nl/locaties"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            items = _extract_js_json(resp.text, "locations")
            for item in items:
                name    = str(item.get("name") or "").strip()
                address = str(item.get("address") or "").strip()
                zipcode = str(item.get("zipcode") or "").strip()
                # zipcode may be "1091 RV, Amsterdam" or just "1091RV"
                pc_m = POSTCODE_RE.search(zipcode)
                postcode = pc_m.group(1).replace(" ", "") if pc_m else ""
                # City after the postcode in the zipcode string, or separate field
                city_m = re.search(r"\d{4}\s*[A-Z]{2}[,\s]+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{2,40})", zipcode)
                city = city_m.group(1).strip() if city_m else (item.get("city") or "").strip()
                if not city:
                    city = (item.get("url") or "").split("/locaties/")[-1].split("/")[0].replace("-", " ").title()
                if name and (city or postcode):
                    locations.append({
                        "name": name, "street": address,
                        "postcode": postcode, "city": city,
                    })

            if locations:
                logger.info(f"[compananny-branches] {len(locations)} locations from JS array at {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[compananny-branches] {url} failed: {exc}")

    return locations


def scrape_tinteltuin_vestigingen() -> list[dict]:
    """
    Scrape TintelTuin branches from tinteltuin.nl/kinderopvang.
    The page embeds a JavaScript array with location name + adres (full address).
    """
    locations = []
    for url in ["https://tinteltuin.nl/kinderopvang", "https://www.tinteltuin.nl/kinderopvang"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            # TintelTuin embeds location data as a JS array; adres contains "Street, POSTCODE City"
            items = _extract_js_json(resp.text, "locations") or _extract_js_json(resp.text, "locaties")
            if not items:
                # Try to find any JSON-like array with 'adres' key
                m = re.search(r'\[\s*\{[^]]*"adres"[^]]*\}[^]]*\]', resp.text, re.DOTALL)
                if m:
                    import json as _json
                    try:
                        items = _json.loads(m.group(0))
                    except Exception:
                        pass

            for item in items:
                name  = str(item.get("name") or item.get("naam") or "").strip()
                adres = str(item.get("adres") or item.get("address") or "").strip()
                if not adres:
                    continue
                street, postcode, city = _parse_address_block(adres)
                if not city:
                    pc_m = POSTCODE_RE.search(adres)
                    postcode = pc_m.group(1).replace(" ", "") if pc_m else ""
                if name and (city or postcode):
                    locations.append({
                        "name": name, "street": street,
                        "postcode": postcode, "city": city,
                    })

            if locations:
                logger.info(f"[tinteltuin-branches] {len(locations)} locations at {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[tinteltuin-branches] {url} failed: {exc}")

    return locations


def scrape_sinne_vestigingen() -> list[dict]:
    """
    Scrape Sinne branches from sinnekinderopvang.nl/contact/vind-een-locatie.
    Page embeds window.ProjectenData with headline + adres (full address).
    """
    locations = []
    for url in [
        "https://www.sinnekinderopvang.nl/contact/vind-een-locatie",
        "https://www.sinnekinderopvang.nl/locaties",
    ]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            items = _extract_js_json(resp.text, "window.ProjectenData") or \
                    _extract_js_json(resp.text, "ProjectenData")
            if not items:
                # Also look for JSON-like array with headline+adres pattern
                m = re.search(r'ProjectenData\s*=\s*(\[[\s\S]*?\])\s*[;\n]', resp.text)
                if m:
                    import json as _json
                    try:
                        items = _json.loads(m.group(1))
                    except Exception:
                        pass

            for item in items:
                name = str(item.get("headline") or item.get("name") or "").strip()
                adres = str(item.get("adres") or item.get("address") or "").strip()
                if not adres:
                    continue
                street, postcode, city = _parse_address_block(adres)
                if not postcode:
                    pc_m = POSTCODE_RE.search(adres)
                    postcode = pc_m.group(1).replace(" ", "") if pc_m else ""
                if name and (city or postcode):
                    locations.append({
                        "name": name, "street": street,
                        "postcode": postcode, "city": city,
                    })

            if locations:
                logger.info(f"[sinne-branches] {len(locations)} locations at {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[sinne-branches] {url} failed: {exc}")

    return locations


def scrape_humankind_vestigingen() -> list[dict]:
    """
    Scrape Humankind branches from humankind.nl/vestigingen.
    Page embeds Leaflet GeoJSON features with address in popup HTML.
    Uses sitemap.xml to enumerate 500+ individual location pages as fallback.
    """
    import json as _json
    locations = []

    # Try main vestigingen overview page (Leaflet data)
    for url in ["https://www.humankind.nl/vestigingen", "https://humankind.nl/vestigingen"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            # Extract Leaflet features array
            m = re.search(r'"features"\s*:\s*(\[[\s\S]*?\])\s*[,}]', resp.text, re.DOTALL)
            if m:
                try:
                    features = _json.loads(m.group(1))
                    for feat in features:
                        popup_html = feat.get("popup", "")
                        label = feat.get("label", "")
                        if popup_html:
                            soup = BeautifulSoup(popup_html, "lxml")
                            text = soup.get_text(separator=" ", strip=True)
                            street, postcode, city = _parse_address_block(text)
                            if postcode or city:
                                name = label or feat.get("title", "")
                                locations.append({
                                    "name": name or f"{street}, {city}",
                                    "street": street,
                                    "postcode": postcode,
                                    "city": city,
                                })
                except Exception:
                    pass

            # HTML fallback: cards with address
            if not locations:
                soup = BeautifulSoup(resp.text, "lxml")
                for card in soup.select("article, .location-card, [class*='vestiging']"):
                    name_el = card.select_one("h2, h3, h4, strong")
                    name = name_el.get_text(strip=True) if name_el else ""
                    text = card.get_text(separator="\n")
                    street, postcode, city = _parse_address_block(text)
                    if name and (postcode or city):
                        locations.append({
                            "name": name, "street": street,
                            "postcode": postcode, "city": city,
                        })

            if locations:
                logger.info(f"[humankind-branches] {len(locations)} locations at {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[humankind-branches] {url} failed: {exc}")

    return locations


# ── Company configs ───────────────────────────────────────────────────────────

def _generic(slug: str, *sites: str) -> dict:
    """Helper: build a COMPANY_CONFIGS entry using _scrape_generic_vestigingen."""
    paths = ["/vestigingen", "/locaties", "/onze-locaties", "/kinderopvang/vestigingen",
             "/kinderopvang/locaties", "/over-ons/vestigingen"]
    return {
        "scraper": lambda s=slug, ss=sites: next(
            (locs for base in ss
             for locs in [_scrape_generic_vestigingen(s, base, paths)] if locs),
            [],
        ),
    }


COMPANY_CONFIGS = {
    # ── custom scrapers ───────────────────────────────────────────────────────
    "partou": {
        "scraper": scrape_partou_vestigingen,
    },
    "kinderdam": {
        "scraper": scrape_kinderdam_vestigingen,
    },
    # ── generic scrapers ──────────────────────────────────────────────────────
    "spring": _generic(
        "spring",
        "https://www.spring-kinderopvang.nl",
    ),
    "prokino": _generic(
        "prokino",
        "https://www.prokino.nl",
    ),
    "norlandia": _generic(
        "norlandia",
        "https://www.norlandia.nl",
    ),
    "gro-up": _generic(
        "gro-up",
        "https://www.gro-up.nl",
    ),
    "compananny": {"scraper": scrape_compananny_vestigingen},
    "sinne":      {"scraper": scrape_sinne_vestigingen},
    "tinteltuin": {"scraper": scrape_tinteltuin_vestigingen},
    "humankind":  {"scraper": scrape_humankind_vestigingen},
    "kibeo": _generic(
        "kibeo",
        "https://www.kibeo.nl",
    ),
    "kindergarden": _generic(
        "kindergarden",
        "https://www.kindergarden.nl",
        "https://www.werkenbijkindergarden.nl",
    ),
    "bijdehandjes": _generic(
        "bijdehandjes",
        "https://www.bijdehandjes.nl",
    ),
    "bink": _generic(
        "bink",
        "https://www.binkopvang.nl",
        "https://www.bink.nl",
    ),
    "dak": _generic(
        "dak",
        "https://www.dakkindercentra.nl",
    ),
    "dichtbij": _generic(
        "dichtbij",
        "https://www.kdv-dichtbij.nl",
        "https://www.dichtbijkinderopvang.nl",
    ),
    "kinderwoud": _generic(
        "kinderwoud",
        "https://www.kinderwoud.nl",
    ),
    "kids-first": _generic(
        "kids-first",
        "https://www.kidsfirstkinderopvang.nl",
        "https://www.kidsfirst.nl",
    ),
    "kober": _generic(
        "kober",
        "https://www.kober.nl",
    ),
    "mik": _generic(
        "mik",
        "https://www.mik-nijmegen.nl",
    ),
    "op-stoom": _generic(
        "op-stoom",
        "https://www.op-stoom.nl",
    ),
    "ska": _generic(
        "ska",
        "https://www.ska.nl",
    ),
    "2samen": _generic(
        "2samen",
        "https://www.2samen.nl",
    ),
    "wasko": _generic(
        "wasko",
        "https://www.wasko.nl",
    ),
    "wij-zijn-jong": _generic(
        "wij-zijn-jong",
        "https://www.korein.nl",
        "https://www.wijzijnjong.nl",
    ),
    "kanteel": _generic(
        "kanteel",
        "https://www.kanteel.nl",
    ),
    "ko-walcheren": _generic(
        "ko-walcheren",
        "https://www.kinderopvangwalcheren.nl",
    ),
    "samenwerkende-ko": _generic(
        "samenwerkende-ko",
        "https://www.samenwerkendekinderopvang.nl",
    ),
    "kion": _generic(
        "kion",
        "https://www.kion.nl",
    ),
}


# ── Main run function ─────────────────────────────────────────────────────────

def run_vestigingen_scrape(company_slugs: list[str] | None = None) -> dict:
    """
    Scrape branches for the given companies (or all if None).
    Geocodes each branch and stores it in the jobs_vestiging table.
    Returns per-company statistics.

    Note: the jobs_vestiging table is created by Django migration 0007_vestiging.
    """
    if company_slugs is None:
        company_slugs = list(COMPANY_CONFIGS.keys())

    conn = get_connection()
    stats = {}

    try:
        with conn:
            cur = conn.cursor()

            for slug in company_slugs:
                config = COMPANY_CONFIGS.get(slug)
                if not config:
                    logger.warning(f"[branches] No config for '{slug}'")
                    continue

                logger.info(f"[branches] Scraping {slug}...")
                try:
                    locations = config["scraper"]()
                except Exception as exc:
                    logger.error(f"[branches] {slug} scraper error: {exc}")
                    stats[slug] = {"error": str(exc)}
                    continue

                inserted = 0
                for loc in locations:
                    try:
                        upsert_vestiging(
                            cur,
                            company_slug=slug,
                            name=loc["name"],
                            street=loc.get("street", ""),
                            postcode=loc.get("postcode", ""),
                            city=loc["city"],
                        )
                        inserted += 1
                        time.sleep(0.2)  # PDOK rate limiting
                    except Exception as exc:
                        logger.warning(f"[branches] Upsert failed for {loc.get('name')}: {exc}")

                stats[slug] = {"locations": inserted}
                logger.info(f"[branches] {slug}: {inserted} branches saved")

    finally:
        conn.close()

    return stats
