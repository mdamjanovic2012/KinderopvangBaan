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
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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
                     postcode: str, city: str,
                     lon: float | None = None, lat: float | None = None) -> None:
    """Upsert a branch record. Uses provided lon/lat or geocodes via PDOK."""
    if lon is None or lat is None:
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
                (company_slug, name, street, postcode, city, location,
                 geocoded_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    NOW(), NOW(), NOW())
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
                (company_slug, name, street, postcode, city, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (company_slug, name) DO UPDATE SET
                street     = EXCLUDED.street,
                postcode   = EXCLUDED.postcode,
                city       = EXCLUDED.city,
                updated_at = EXCLUDED.updated_at
        """, (company_slug, name, street, postcode, city))


def match_vestiging(
    cur, company_slug: str, location_name: str, city: str, title: str = ""
) -> dict | None:
    """
    Find precise branch address for a job vacancy.
    Returns {street, postcode, city, lon, lat} or None.

    Matching order:
      1. Exact / partial name match on location_name
      2. Branch name extracted from |-separated job title
      3. City + title part combination
      4. City fallback — first branch alphabetically (gives a real postcode)
    """

    def _row(row) -> dict:
        return {
            "street":   row[0] or "",
            "postcode": row[1] or "",
            "city":     row[2] or "",
            "lon":      row[3],
            "lat":      row[4],
        }

    # 1. Exact name match on location_name
    if location_name:
        cur.execute("""
            SELECT street, postcode, city,
                   ST_X(location::geometry) AS lon,
                   ST_Y(location::geometry) AS lat
            FROM jobs_vestiging
            WHERE company_slug = %s
              AND LOWER(TRIM(name)) = LOWER(TRIM(%s))
              AND location IS NOT NULL
        """, (company_slug, location_name))
        row = cur.fetchone()
        if row:
            return _row(row)

        # Partial match — alleen als branch naam de location_name bevat
        cur.execute("""
            SELECT street, postcode, city,
                   ST_X(location::geometry) AS lon,
                   ST_Y(location::geometry) AS lat
            FROM jobs_vestiging
            WHERE company_slug = %s
              AND LOWER(name) LIKE LOWER(%s)
              AND location IS NOT NULL
            LIMIT 1
        """, (company_slug, f"%{location_name}%"))
        row = cur.fetchone()
        if row:
            return _row(row)

    # 2. Title-based branch name extraction ("Type | BranchName | Role")
    _TYPE_PREFIXES = {
        "kdv", "bso", "ikc", "kindcentrum", "kinderdagverblijf", "kinderopvang",
        "speelgroep", "peutergroep", "peuterspeelzaal", "buitenschoolseopvang",
        "dagopvang", "gastouderbureau", "vso",
    }

    def _title_candidates(t: str) -> list[str]:
        """Geeft zoektermen op basis van job-titel: volledige deel + variant zonder type-prefix."""
        parts = [p.strip() for p in t.split("|") if p.strip() and len(p.strip()) >= 3]
        candidates = list(parts)
        for part in parts:
            words = part.split()
            if words and words[0].lower().rstrip(".") in _TYPE_PREFIXES and len(words) > 1:
                candidates.append(" ".join(words[1:]))
        return candidates

    title_parts = _title_candidates(title) if title else []

    for part in title_parts:
        cur.execute("""
            SELECT street, postcode, city,
                   ST_X(location::geometry) AS lon,
                   ST_Y(location::geometry) AS lat
            FROM jobs_vestiging
            WHERE company_slug = %s
              AND (LOWER(TRIM(name)) = LOWER(TRIM(%s))
                   OR LOWER(name) LIKE LOWER(%s)
                   OR LOWER(%s) LIKE LOWER(CONCAT('%%', name, '%%')))
              AND location IS NOT NULL
            LIMIT 1
        """, (company_slug, part, f"%{part}%", part))
        row = cur.fetchone()
        if row:
            return _row(row)

    # 2b. Specifieke woorden uit de titel als branch-fragment zoeken
    #     Nuttig voor titels als "PM bij KDV Zijlwatering" → branch "Norlandia BSO Zijlwatering – Wassenaar"
    if title:
        _STOPWORDS = {
            "de", "het", "een", "van", "bij", "voor", "met", "aan", "op",
            "zijn", "haar", "als", "ook", "maar", "nog", "dan", "wel",
            "niet", "dit", "dat", "die", "deze", "om", "en", "of", "in",
            "te", "naar", "uit", "over", "door", "per", "tot", "na",
            "pedagogisch", "medewerker", "professional", "werken", "werk",
            "vacature", "fulltime", "parttime", "flex", "tijdelijk",
            "zoekt", "jou", "zoek", "groep", "babygroep", "verticale",
        }
        title_words = [
            w for w in re.sub(r"[^\w\s]", " ", title).split()
            if len(w) >= 5 and w.lower() not in _STOPWORDS
        ]
        for word in title_words:
            cur.execute("""
                SELECT street, postcode, city,
                       ST_X(location::geometry) AS lon,
                       ST_Y(location::geometry) AS lat
                FROM jobs_vestiging
                WHERE company_slug = %s
                  AND LOWER(name) LIKE LOWER(%s)
                  AND location IS NOT NULL
                ORDER BY LENGTH(name) DESC
                LIMIT 1
            """, (company_slug, f"%{word}%"))
            row = cur.fetchone()
            if row:
                return _row(row)

    # 3. City match
    if city:
        # City + title part combination
        for part in title_parts:
            cur.execute("""
                SELECT street, postcode, city,
                       ST_X(location::geometry) AS lon,
                       ST_Y(location::geometry) AS lat
                FROM jobs_vestiging
                WHERE company_slug = %s
                  AND LOWER(TRIM(city)) = LOWER(TRIM(%s))
                  AND (LOWER(TRIM(name)) = LOWER(TRIM(%s))
                       OR LOWER(name) LIKE LOWER(%s)
                       OR LOWER(%s) LIKE LOWER(CONCAT('%%', name, '%%')))
                  AND location IS NOT NULL
                LIMIT 1
            """, (company_slug, city, part, f"%{part}%", part))
            row = cur.fetchone()
            if row:
                return _row(row)

        # City-only fallback — first branch alphabetically gives a real address
        cur.execute("""
            SELECT street, postcode, city,
                   ST_X(location::geometry) AS lon,
                   ST_Y(location::geometry) AS lat
            FROM jobs_vestiging
            WHERE company_slug = %s
              AND LOWER(TRIM(city)) = LOWER(TRIM(%s))
              AND location IS NOT NULL
            ORDER BY name
            LIMIT 1
        """, (company_slug, city))
        row = cur.fetchone()
        if row:
            return _row(row)

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


def _parse_comma_address(text: str) -> tuple[str, str, str]:
    """
    Parse an address in comma-separated format:
    'Pieter de Hooghstraat 6, 5854 ES, Bergen' → (street, postcode, city)
    Also handles '5854 ES Bergen' without comma before city.
    """
    pc_m = POSTCODE_RE.search(text)
    if not pc_m:
        return "", "", ""
    postcode = pc_m.group(1).replace(" ", "")
    street = text[:pc_m.start()].strip().rstrip(",").strip()
    after = text[pc_m.end():].strip().lstrip(",").strip()
    # Take up to first comma or end of string
    city = re.split(r"[,\n]", after)[0].strip()
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

    # Deduplicate by physical address (address+postcode+city).
    # Multiple vacancies at the same location have different oeNumbers (KDV, BSO, PSZ)
    # but represent the same branch → use address as primary key.
    seen: dict[str, dict] = {}
    for item in items:
        address  = (item.get("address") or "").strip()
        postcode = (item.get("postalCode") or "").replace(" ", "").strip()
        city     = (item.get("city") or "").strip()

        if not city or not (address or postcode):
            continue

        key = f"{address}|{postcode}|{city}"
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
    The page embeds a JS object literal array (not JSON) with lon/lat/address per location.
    Uses regex extraction since keys are unquoted and strings use single quotes.
    """
    locations = []
    for url in ["https://www.compananny.com/locaties", "https://www.compananny.nl/locaties"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            # JS object literal: name: 'X', lon: 'X', lat: 'X', address: 'X', zipcode: 'X, City'
            entries = re.findall(
                r"name:\s*'([^']+)'[^}]*?lon:\s*'([^']+)'[^}]*?lat:\s*'([^']+)'[^}]*?"
                r"address:\s*'([^']*)'[^}]*?zipcode:\s*'([^']*)'",
                resp.text, re.DOTALL,
            )
            for name, lon, lat, address, zipcode in entries:
                pc_m = POSTCODE_RE.search(zipcode)
                postcode = pc_m.group(1).replace(" ", "") if pc_m else ""
                city_m = re.search(r"\d{4}\s*[A-Z]{2}[,\s]+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{2,40})", zipcode)
                city = city_m.group(1).strip() if city_m else ""
                if name and (city or postcode):
                    loc = {
                        "name": name.strip(), "street": address.strip(),
                        "postcode": postcode, "city": city,
                    }
                    try:
                        loc["lon"] = float(lon)
                        loc["lat"] = float(lat)
                    except ValueError:
                        pass
                    locations.append(loc)

            if locations:
                logger.info(f"[compananny-branches] {len(locations)} locations from JS at {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[compananny-branches] {url} failed: {exc}")

    return locations


def scrape_tinteltuin_vestigingen() -> list[dict]:
    """
    Scrape TintelTuin branches from tinteltuin.nl/kinderopvang.
    Page embeds a 'mapdata' JSON array with addresses.map.lat/lng per location.
    """
    import json as _json
    locations = []
    for url in ["https://tinteltuin.nl/kinderopvang", "https://www.tinteltuin.nl/kinderopvang"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            m = re.search(r'mapdata\s*=\s*(\[[\s\S]*?\])\s*;', resp.text)
            if not m:
                continue
            try:
                items = _json.loads(m.group(1))
            except Exception:
                continue

            for item in items:
                name    = str(item.get("post_title") or "").strip()
                addrs   = item.get("addresses") or {}
                street  = str(addrs.get("street_name") or "").strip()
                postcode = str(addrs.get("postcode") or "").replace(" ", "").strip()
                city    = str(addrs.get("city") or "").strip()
                map_data = addrs.get("map") or {}
                lat = map_data.get("lat")
                lon = map_data.get("lng")
                # Fallback: addresses.postcode is sometimes incomplete (e.g. '1509' without letters)
                if map_data.get("post_code") and not re.match(r"^\d{4}[A-Z]{2}$", postcode):
                    postcode = map_data["post_code"].replace(" ", "")
                if name and (city or postcode):
                    loc = {"name": name, "street": street, "postcode": postcode, "city": city}
                    if lat and lon:
                        try:
                            loc["lat"] = float(lat)
                            loc["lon"] = float(lon)
                        except ValueError:
                            pass
                    locations.append(loc)

            if locations:
                logger.info(f"[tinteltuin-branches] {len(locations)} locations at {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[tinteltuin-branches] {url} failed: {exc}")

    return locations


def scrape_sinne_vestigingen() -> list[dict]:
    """
    Scrape Sinne branches from sinnekinderopvang.nl/contact/vind-een-locatie.
    Page embeds ProjectenData JSON array; address in properties.values.adres (HTML),
    coordinates in properties.values.latitude/longitude.
    """
    import json as _json
    locations = []
    for url in [
        "https://www.sinnekinderopvang.nl/contact/vind-een-locatie",
        "https://www.sinnekinderopvang.nl/locaties",
    ]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            m = re.search(r'ProjectenData\s*=\s*(\[[\s\S]*?\])\s*[;\n]', resp.text)
            if not m:
                continue
            try:
                items = _json.loads(m.group(1))
            except Exception:
                continue

            for item in items:
                name = str(item.get("headline") or "").strip()
                props_vals = (item.get("properties") or {}).get("values") or {}
                adres_html = str(props_vals.get("adres") or "").strip()
                lat_str    = str(props_vals.get("latitude") or "")
                lon_str    = str(props_vals.get("longitude") or "")

                # Strip HTML tags from adres
                adres_text = re.sub(r"<[^>]+>", " ", adres_html).strip()
                adres_text = re.sub(r"\s+", " ", adres_text).strip()

                street, postcode, city = _parse_address_block(adres_text)
                if not postcode:
                    pc_m = POSTCODE_RE.search(adres_text)
                    postcode = pc_m.group(1).replace(" ", "") if pc_m else ""

                if name and (city or postcode):
                    loc = {"name": name, "street": street, "postcode": postcode, "city": city}
                    try:
                        loc["lat"] = float(lat_str)
                        loc["lon"] = float(lon_str)
                    except (ValueError, TypeError):
                        pass
                    locations.append(loc)

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


# ── Additional custom scrapers ────────────────────────────────────────────────

def scrape_spring_vestigingen() -> list[dict]:
    """
    Scrape Spring branches from spring-kinderopvang.nl/locaties.
    Each article has data-geocode='lat, lng' and .card-title for name,
    and a <span> in .card-text with 'street, postcode, city'.
    """
    locations = []
    for url in ["https://www.spring-kinderopvang.nl/locaties",
                "https://spring-kinderopvang.nl/locaties"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select("article[data-geocode]"):
                name_el = card.select_one(".card-title, a.card-title, h5, h4, h3, h2")
                name = name_el.get_text(strip=True) if name_el else ""
                if not name:
                    continue
                addr_el = card.select_one(".card-text span, .fw-300 span")
                addr_text = addr_el.get_text(strip=True) if addr_el else ""
                street, postcode, city = _parse_comma_address(addr_text)
                geo = card.get("data-geocode", "")
                lat = lon = None
                if geo:
                    parts = geo.split(",")
                    if len(parts) == 2:
                        try:
                            lat = float(parts[0].strip())
                            lon = float(parts[1].strip())
                        except ValueError:
                            pass
                if name and (city or postcode):
                    loc = {"name": name, "street": street, "postcode": postcode, "city": city}
                    if lat and lon:
                        loc["lat"] = lat
                        loc["lon"] = lon
                    locations.append(loc)
            if locations:
                logger.info(f"[spring-branches] {len(locations)} locations at {url}")
                return locations
        except Exception as exc:
            logger.warning(f"[spring-branches] {url} failed: {exc}")
    return locations


def scrape_prokino_vestigingen() -> list[dict]:
    """
    Scrape Prokino from prokino.nl/locaties using Next.js __NEXT_DATA__.
    Each location has geoLocation.lat/lng and contactDetails.address/zipCode/city.
    """
    import json as _json
    locations = []
    url = "https://www.prokino.nl/locaties"
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            resp.text, re.DOTALL,
        )
        if not m:
            return []
        data = _json.loads(m.group(1))
        locs_raw = (data.get("props", {}).get("pageProps", {})
                    .get("pageProps", {}).get("locations", []))
        seen = set()
        for item in locs_raw:
            name = str(item.get("pageTitle") or "").strip()
            geo = item.get("geoLocation") or {}
            lat = geo.get("lat")
            lng = geo.get("lng")
            # Get contactDetails — prefer first product with a zipCode
            products = []
            for section in (item.get("sectionBox") or []):
                products.extend(section.get("products") or [])
            contact = {}
            for prod in products:
                cd = prod.get("contactDetails") or {}
                if cd.get("zipCode", "").strip():
                    contact = cd
                    break
            if not contact and products:
                contact = products[0].get("contactDetails") or {}
            street   = str(contact.get("address") or "").strip()
            zipcode  = str(contact.get("zipCode") or "").replace(" ", "").strip()
            city     = str(contact.get("city") or "").strip()
            if not city:
                city = str((item.get("parent") or {}).get("pageTitle") or "").strip()
            if not zipcode:
                continue  # geen postcode → niet bruikbaar voor geocodering
            key = f"{zipcode}|{street}"
            if name and (city or zipcode) and key not in seen:
                seen.add(key)
                loc = {"name": name, "street": street, "postcode": zipcode, "city": city}
                if lat and lng:
                    try:
                        loc["lat"] = float(lat)
                        loc["lon"] = float(lng)
                    except (ValueError, TypeError):
                        pass
                locations.append(loc)
        logger.info(f"[prokino-branches] {len(locations)} locations from Next.js")
    except Exception as exc:
        logger.warning(f"[prokino-branches] {url} failed: {exc}")
    return locations


def scrape_kober_vestigingen() -> list[dict]:
    """
    Scrape Kober from kober.nl/locaties.
    Each location card has .right-col with h5.post-title (name) and
    .address-wrapper span.address with 'street, postcode, city'.
    """
    locations = []
    for url in ["https://kober.nl/locaties", "https://www.kober.nl/locaties"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            seen = set()
            for addr_span in soup.select("span.address"):
                addr_text = addr_span.get_text(strip=True)
                if not re.search(r"\d{4}\s?[A-Z]{2}", addr_text):
                    continue
                # Find name in parent .right-col
                right_col = addr_span.find_parent(class_=lambda c: c and "right-col" in (c if isinstance(c, str) else " ".join(c)))
                if not right_col:
                    right_col = addr_span.find_parent(["article", "div", "li"])
                name_el = right_col.select_one("h5, h4, h3, h2, .post-title") if right_col else None
                name = name_el.get_text(strip=True) if name_el else ""
                street, postcode, city = _parse_comma_address(addr_text)
                key = f"{postcode}|{name}"
                if name and (city or postcode) and key not in seen:
                    seen.add(key)
                    locations.append({"name": name, "street": street, "postcode": postcode, "city": city})
            if locations:
                logger.info(f"[kober-branches] {len(locations)} locations at {url}")
                return locations
        except Exception as exc:
            logger.warning(f"[kober-branches] {url} failed: {exc}")
    return locations


def scrape_kion_vestigingen() -> list[dict]:
    """
    Scrape KION from kion.nl/locaties.
    Page embeds a JS object literal array (single quotes) with
    id/type/name/address/city/zipcode/lat/lng per location.
    """
    locations = []
    for url in ["https://kion.nl/locaties", "https://www.kion.nl/locaties"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            # JS single-quoted object literals in an array
            entries = re.findall(
                r"\{\s*'id':\s*(\d+)[^}]*?"
                r"'name':\s*'([^']*)'[^}]*?"
                r"'address':\s*'([^']*)'[^}]*?"
                r"'city':\s*'([^']*)'[^}]*?"
                r"'zipcode':\s*'([^']*)'[^}]*?"
                r"'lat':\s*([\d\.\-]+)[^}]*?"
                r"'lng':\s*([\d\.\-]+)",
                resp.text, re.DOTALL,
            )
            seen = set()
            for _id, name, address, city, zipcode, lat, lng in entries:
                postcode = zipcode.replace(" ", "").strip()
                key = f"{postcode}|{name}"
                if name and (city or postcode) and key not in seen:
                    seen.add(key)
                    loc = {"name": name, "street": address.strip(), "postcode": postcode, "city": city.strip()}
                    try:
                        loc["lat"] = float(lat)
                        loc["lon"] = float(lng)
                    except ValueError:
                        pass
                    locations.append(loc)
            if locations:
                logger.info(f"[kion-branches] {len(locations)} locations at {url}")
                return locations
        except Exception as exc:
            logger.warning(f"[kion-branches] {url} failed: {exc}")
    return locations


def scrape_kinderdam_vestigingen() -> list[dict]:
    """
    Scrape KindeRdam from kinderdam.nl/locaties (Next.js App Router / flight protocol).
    Decodes self.__next_f.push() calls, finds 'locations' JSON array, then extracts
    each item's name and kdv/bso/po sub-object with address/postalCode/city/lat/lng.
    """
    import json as _json
    locations = []
    for url in ["https://kinderdam.nl/locaties", "https://www.kinderdam.nl/locaties"]:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            pushes = re.findall(
                r'self\.__next_f\.push\(\[1,"(.*?)"\]\)',
                resp.text, re.DOTALL,
            )
            if not pushes:
                continue
            full = "".join(pushes).encode("utf-8").decode("unicode_escape", errors="replace")

            # Find 'locations' array and parse it
            m = re.search(r'"locations"\s*:\s*\[', full)
            if not m:
                continue
            start = m.end() - 1  # point to the '['
            depth = 0
            end = start
            for i, c in enumerate(full[start:], start):
                if c == "[":
                    depth += 1
                elif c == "]":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            try:
                items = _json.loads(full[start:end])
            except Exception:
                continue

            seen: set[str] = set()
            for item in items:
                name = str(item.get("name") or "").strip()
                # Pick first care-type sub-object that has address data
                contact: dict = {}
                for care_key in ("kdv", "bso", "po", "ssg"):
                    sub = item.get(care_key) or {}
                    if sub.get("address") or sub.get("postalCode"):
                        contact = sub
                        break
                if not contact:
                    continue
                address  = str(contact.get("address") or "").strip()
                postcode = str(contact.get("postalCode") or "").replace(" ", "").strip()
                city     = str(contact.get("city") or "").strip()
                lat      = contact.get("latitude")
                lng      = contact.get("longitude")
                key = f"{postcode}|{address}"
                if name and (city or postcode) and key not in seen:
                    seen.add(key)
                    loc = {"name": name, "street": address, "postcode": postcode, "city": city}
                    if lat and lng:
                        try:
                            loc["lat"] = float(lat)
                            loc["lon"] = float(lng)
                        except (ValueError, TypeError):
                            pass
                    locations.append(loc)

            if locations:
                logger.info(f"[kinderdam-branches] {len(locations)} locations at {url}")
                return locations
        except Exception as exc:
            logger.warning(f"[kinderdam-branches] {url} failed: {exc}")
    return locations


def scrape_kindergarden_vestigingen() -> list[dict]:
    """
    Kindergarden (kindergarden.nl) — JSON API /api/locations.
    Returns all 76+ locations with full address + coordinates.
    """
    url = "https://www.kindergarden.nl/api/locations?sc_device=json"
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"[kindergarden-branches] API failed: {exc}")
        return []

    seen: set[str] = set()
    locations = []
    for item in data.get("Locations", []):
        name     = (item.get("Name") or "").strip()
        street   = (item.get("Address") or "").strip()
        postcode = (item.get("PostalCode") or "").replace(" ", "")
        city     = (item.get("City") or "").strip()
        lat      = float(item["Latitude"])  if item.get("Latitude")  else None
        lon      = float(item["Longitude"]) if item.get("Longitude") else None

        if not name or not (postcode or city):
            continue
        key = f"{name}|{postcode}"
        if key in seen:
            continue
        seen.add(key)
        locations.append({
            "name": name, "street": street,
            "postcode": postcode, "city": city,
            "lon": lon, "lat": lat,
        })

    logger.info(f"[kindergarden-branches] {len(locations)} locations from API")
    return locations


def scrape_ko_walcheren_vestigingen() -> list[dict]:
    """
    KO Walcheren (kinderopvangwalcheren.nl) — HTML list with .location-teaser__inner cards.
    Each card has a title and address: "Street 5, 1234AB City".
    """
    url = "https://www.kinderopvangwalcheren.nl/locaties"
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning(f"[ko-walcheren-branches] fetch failed: {exc}")
        return []

    seen: set[str] = set()
    locations = []
    for card in soup.select(".location-teaser__inner"):
        title_el = card.select_one(".location-teaser__title")
        addr_el  = card.select_one(".location-teaser__address")
        if not title_el or not addr_el:
            continue

        name      = title_el.get_text(strip=True)
        addr_text = addr_el.get_text(strip=True)
        m_pc = POSTCODE_RE.search(addr_text)
        if not m_pc:
            continue

        postcode  = m_pc.group(1).replace(" ", "")
        city      = addr_text[m_pc.end():].strip().lstrip(",").strip()
        street    = addr_text[:m_pc.start()].rstrip(", ")

        if not name or not postcode:
            continue
        key = f"{name}|{postcode}"
        if key in seen:
            continue
        seen.add(key)
        locations.append({
            "name": name, "street": street,
            "postcode": postcode, "city": city,
            "lon": None, "lat": None,
        })

    logger.info(f"[ko-walcheren-branches] {len(locations)} locations from HTML")
    return locations


def scrape_mik_vestigingen() -> list[dict]:
    """
    MIK (mik-nijmegen.nl → redirects to mik-spelenderwijs.nl) — HTML list page.
    Each item: <h4>Name</h4><span>Street - PostcodeCity</span>
    """
    url = "https://www.mik-spelenderwijs.nl/locaties"
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning(f"[mik-branches] fetch failed: {exc}")
        return []

    seen: set[str] = set()
    locations = []
    # Location list items: <li><a href="..."><h4>Name</h4><span>Addr - PostcodeCity</span></a></li>
    for li in soup.select("li[wire\\:key]"):
        h4 = li.select_one("h4")
        span = li.select_one("span")
        if not h4 or not span:
            continue

        name = h4.get_text(strip=True)
        addr_text = span.get_text(strip=True)  # "Lindenlaan 73 - 6241BB Bunde"

        # Format: "Street NR - PostcodeCity"
        m_pc = POSTCODE_RE.search(addr_text)
        if not m_pc:
            continue

        postcode  = m_pc.group(1).replace(" ", "")
        city      = addr_text[m_pc.end():].strip()
        street    = addr_text[:m_pc.start()].rstrip(" -").strip()

        if not name or not postcode:
            continue
        key = f"{name}|{postcode}"
        if key in seen:
            continue
        seen.add(key)
        locations.append({
            "name": name, "street": street,
            "postcode": postcode, "city": city,
            "lon": None, "lat": None,
        })

    logger.info(f"[mik-branches] {len(locations)} locations from HTML")
    return locations


def scrape_norlandia_vestigingen() -> list[dict]:
    """
    Norlandia kinderopvang (norlandia.nl) — city sub-pages with embedded JSON.
    Strategy:
      1. Fetch /zoek-locatie to get list of all city URLs.
      2. For each city URL fetch the page and extract the Items array from the model,
         which contains Address, ZipCode, Position (lat/lon) per location.
    """
    import json as _json

    base = "https://norlandia.nl"
    try:
        resp = requests.get(f"{base}/zoek-locatie", headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
        m = re.search(r'"Cities"\s*:\s*(\[.*?\])\s*[,}]', resp.text, re.DOTALL)
        if not m:
            logger.warning("[norlandia-branches] Could not find Cities array on zoek-locatie")
            return []
        cities = _json.loads(m.group(1))
    except Exception as exc:
        logger.warning(f"[norlandia-branches] Failed to fetch city list: {exc}")
        return []

    seen: set[str] = set()
    locations = []

    for city_obj in cities:
        city_url = base + city_obj.get("Url", "")
        try:
            r = requests.get(city_url, headers=SCRAPER_HEADERS, timeout=20)
            if r.status_code != 200:
                continue
            # Find the second 'var model' block (first is the search widget, second has MapHits)
            idx = r.text.find('var model = {', r.text.find('ViewOtherLocationsText') - 200)
            if idx < 0:
                idx = r.text.rfind('var model = {')
            if idx < 0:
                continue
            brace_start = r.text.index('{', idx)
            depth = 0
            brace_end = brace_start
            for i in range(brace_start, min(brace_start + 400000, len(r.text))):
                if r.text[i] == '{':
                    depth += 1
                elif r.text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        brace_end = i + 1
                        break
            model = _json.loads(r.text[brace_start:brace_end])
            items = model.get("MapHits", [])
            for item in items:
                name     = (item.get("Name") or "").strip()
                street   = (item.get("Address") or "").strip()
                postcode = (item.get("ZipCode") or "").replace(" ", "")
                city     = (item.get("Municipality") or "").strip()
                pos      = item.get("Position") or {}
                lat      = float(pos["Latitude"])  if pos.get("Latitude")  else None
                lon      = float(pos["Longitude"]) if pos.get("Longitude") else None

                if not name or not (postcode or city):
                    continue
                key = f"{name}|{postcode}"
                if key in seen:
                    continue
                seen.add(key)
                locations.append({
                    "name": name, "street": street,
                    "postcode": postcode, "city": city,
                    "lon": lon, "lat": lat,
                })
            time.sleep(0.3)
        except Exception as exc:
            logger.warning(f"[norlandia-branches] {city_url} failed: {exc}")

    logger.info(f"[norlandia-branches] {len(locations)} locations from city pages")
    return locations


def scrape_bijdehandjes_vestigingen() -> list[dict]:
    """
    BijdeHandjes (bijdehandjes.info) — hidden JSON API used by the location map.
    Endpoint: /api/locations/groups — returns all locations with full address + coordinates.
    """
    url = "https://www.bijdehandjes.info/api/locations/groups"
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"[bijdehandjes-branches] API fetch failed: {exc}")
        return []

    seen: set[str] = set()
    locations = []
    for group in data.get("locations", []):
        name    = (group.get("title") or "").strip()
        address = (group.get("address") or "").strip()
        geo     = group.get("geofield") or {}
        lat     = geo.get("lat")
        lon     = geo.get("lon")

        # address format: "Street 12, 1234AB City"
        street = postcode = city = ""
        if address:
            m_pc = POSTCODE_RE.search(address)
            if m_pc:
                postcode = m_pc.group(1).replace(" ", "")
                before_pc = address[:m_pc.start()].rstrip(", ")
                after_pc  = address[m_pc.end():].lstrip(", ").strip()
                street  = before_pc
                city    = after_pc

        if not name or not (postcode or city):
            continue
        key = f"{name}|{postcode}"
        if key in seen:
            continue
        seen.add(key)

        locations.append({
            "name": name, "street": street,
            "postcode": postcode, "city": city,
            "lon": lon, "lat": lat,
        })

    logger.info(f"[bijdehandjes-branches] {len(locations)} locations from API")
    return locations


def scrape_dak_vestigingen() -> list[dict]:
    """
    DAK kindercentra (dakkindercentra.nl) — GeoJSON endpoint.
    The website's Google Maps widget loads a static GeoJSON file with all locations,
    coordinates and full addresses.
    """
    url = "https://www.dakkindercentra.nl/wp-content/uploads/dakkindercentra/locations.geojson"
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"[dak-branches] GeoJSON fetch failed: {exc}")
        return []

    seen: set[str] = set()
    locations = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        if not props.get("visible", True):
            continue

        name     = (props.get("name") or "").strip()
        address  = (props.get("address") or "").strip()
        postcode = (props.get("postcode") or "").replace(" ", "").strip()
        city     = (props.get("city") or "").strip()

        # address is often "Street 1, 1234AB City" — extract street part
        street = ""
        if address:
            parts = address.split(",")
            if parts:
                street = parts[0].strip()

        coords = feature.get("geometry", {}).get("coordinates", [])
        lon = float(coords[0]) if len(coords) >= 2 else None
        lat = float(coords[1]) if len(coords) >= 2 else None

        if not name or not (postcode or city):
            continue
        key = f"{name}|{postcode}"
        if key in seen:
            continue
        seen.add(key)

        locations.append({
            "name": name, "street": street,
            "postcode": postcode, "city": city,
            "lon": lon, "lat": lat,
        })

    logger.info(f"[dak-branches] {len(locations)} locations from GeoJSON")
    return locations


def scrape_wij_zijn_jong_vestigingen() -> list[dict]:
    """
    Wij zijn JONG / Korein (korein.nl) — JSON POST endpoint.
    The map widget POSTs to /vestigingen/output:json/module:988 and returns
    all 105 locations with lat/lon and markerInfo HTML containing the address.
    """
    url = "https://www.korein.nl/vestigingen/output:json/module:988"
    try:
        resp = requests.post(url, headers=SCRAPER_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"[wij-zijn-jong-branches] POST failed: {exc}")
        return []

    markers = data.get("aMarkers", {})
    locations = []
    seen: set[str] = set()

    for marker in markers.values():
        html = marker.get("markerInfo", "")
        soup = BeautifulSoup(html, "html.parser")

        name_el    = soup.select_one(".gmaps2-markerinfo-title")
        street_el  = soup.select_one(".gmaps2-markerinfo-address")
        postal_el  = soup.select_one(".gmaps2-markerinfo-postal")
        city_el    = soup.select_one(".gmaps2-markerinfo-city")

        name     = (name_el.get_text(strip=True)   if name_el    else "").strip()
        street   = (street_el.get_text(strip=True)  if street_el  else "").strip()
        postcode = (postal_el.get_text(strip=True)   if postal_el  else "").replace(" ", "").strip()
        city     = (city_el.get_text(strip=True)    if city_el    else "").strip()
        lat      = marker.get("latitude")
        lon      = marker.get("longitude")

        if not name or not (postcode or city):
            continue
        key = f"{name}|{postcode}"
        if key in seen:
            continue
        seen.add(key)
        locations.append({
            "name": name, "street": street,
            "postcode": postcode, "city": city,
            "lat": lat, "lon": lon,
        })

    logger.info(f"[wij-zijn-jong-branches] {len(locations)} locations from JSON API")
    return locations


def scrape_wasko_vestigingen() -> list[dict]:
    """
    Wasko (wasko.nl) — WP REST API + individual page HTML.
    The REST API /wp/v2/locatie gives all slugs; the individual pages
    have an <h6> tag: "Locatie | street | postcode city | tel".
    """
    # Fetch all slugs via REST API (pagination)
    slugs: list[str] = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"https://wasko.nl/wp-json/wp/v2/locatie?per_page=100&page={page}&_fields=slug",
                headers=SCRAPER_HEADERS, timeout=20,
            )
            if resp.status_code == 400:
                break  # no more pages
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            slugs.extend(item["slug"] for item in batch)
            page += 1
        except Exception as exc:
            logger.warning(f"[wasko-branches] REST page {page} failed: {exc}")
            break

    locations = []
    seen: set[str] = set()

    for slug in slugs:
        try:
            resp = requests.get(
                f"https://wasko.nl/locatie/{slug}/",
                headers=SCRAPER_HEADERS, timeout=15,
            )
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # Address is in <h6>: "Locatie\nstreet\npostcode city\ntel" (with <br> separators)
            h6 = next(
                (t for t in soup.find_all("h6") if "locatie" in t.get_text().lower()),
                None,
            )
            if not h6:
                continue

            parts = [p.strip() for p in h6.get_text(separator="|").split("|") if p.strip()]
            # parts[0]="Locatie", parts[1]=street, parts[2]="postcode city", ...
            h1 = soup.find("h1")
            name = h1.get_text(strip=True) if h1 else slug

            street = parts[1] if len(parts) > 1 else ""
            postcode_city = parts[2] if len(parts) > 2 else ""

            pc_match = POSTCODE_RE.search(postcode_city)
            if not pc_match:
                continue
            postcode = pc_match.group(1).replace(" ", "")
            city = postcode_city[pc_match.end():].strip()

            key = f"{name}|{postcode}"
            if key in seen:
                continue
            seen.add(key)
            locations.append({
                "name": name, "street": street,
                "postcode": postcode, "city": city,
            })
            time.sleep(0.3)
        except Exception as exc:
            logger.debug(f"[wasko-branches] {slug} failed: {exc}")

    logger.info(f"[wasko-branches] {len(locations)} locations scraped")
    return locations


def scrape_kanteel_vestigingen() -> list[dict]:
    """
    Kanteel (kanteel.nl) — embedded JSON in city list pages.
    Each city page (/locaties/{city}?weergave=lijst) embeds a JSON object
    passed to handleGoogleMaps() with all locations, addresses and coordinates.
    """
    cities = ["den-bosch", "uden", "zaltbommel"]
    locations = []
    seen: set[str] = set()

    for city in cities:
        url = f"https://www.kanteel.nl/locaties/{city}?weergave=lijst"
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20, verify=False)
            resp.raise_for_status()
            m = re.search(r"handleGoogleMaps\('(.+?)'\)", resp.text, re.DOTALL)
            if not m:
                continue

            # Kanteel escapes single quotes as \u0027 — decode unicode escapes
            raw = m.group(1).encode("utf-8").decode("unicode_escape")
            data = __import__("json").loads(raw)
        except Exception as exc:
            logger.warning(f"[kanteel-branches] {city} failed: {exc}")
            continue

        for loc_data in data.get("locations", {}).values():
            name    = (loc_data.get("Name") or "").strip()
            street  = (loc_data.get("Street") or "").strip()
            postal  = (loc_data.get("PostalAndPlace") or "").strip()
            geo     = loc_data.get("Geo") or {}
            lat     = geo.get("latitude")
            lon     = geo.get("longitude")

            pc_match = POSTCODE_RE.search(postal)
            if not pc_match:
                continue
            postcode = pc_match.group(1).replace(" ", "")
            city_name = postal[pc_match.end():].strip()

            if not name:
                continue
            key = f"{name}|{postcode}"
            if key in seen:
                continue
            seen.add(key)
            locations.append({
                "name": name, "street": street,
                "postcode": postcode, "city": city_name,
                "lat": lat, "lon": lon,
            })

    logger.info(f"[kanteel-branches] {len(locations)} locations from embedded JSON")
    return locations


def scrape_gro_up_vestigingen() -> list[dict]:
    """
    Gro-up (gro-up.nl) — sitemap + individual page HTML.
    The sitemap lists individual /locaties/<slug>/ pages; each page has
    a .contact-block__address element with the address.
    Only kinderopvang locations are included (filter out buurtwerk/kraamzorg/jeugdhulp).
    """
    EXCLUDE = {"buurtwerk", "kraamzorg", "jeugdhulp", "actueel"}

    try:
        resp = requests.get("https://www.gro-up.nl/sitemap.xml", headers=SCRAPER_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        urls = [loc.get_text() for loc in soup.find_all("loc")]
    except Exception as exc:
        logger.warning(f"[gro-up-branches] sitemap failed: {exc}")
        return []

    loc_urls = [
        u for u in urls
        if "/locaties/" in u and u.rstrip("/").count("/") >= 4
        and not any(ex in u for ex in EXCLUDE)
    ]
    logger.info(f"[gro-up-branches] {len(loc_urls)} location URLs from sitemap")

    def _fetch_loc(url):
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=15)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            h1 = soup.find("h1")
            name = h1.get_text(strip=True) if h1 else ""
            addr_el = soup.select_one(".contact-block__address")
            if not addr_el or not name:
                return None
            text = addr_el.get_text(separator="\n")
            street, postcode, city = _parse_address_block(text)
            if not postcode and not city:
                return None
            return {"name": name, "street": street, "postcode": postcode, "city": city}
        except Exception as exc:
            logger.debug(f"[gro-up-branches] {url} failed: {exc}")
            return None

    locations = []
    seen: set[str] = set()
    with ThreadPoolExecutor(max_workers=8) as pool:
        for loc in pool.map(_fetch_loc, loc_urls):
            if loc is None:
                continue
            key = f"{loc['name']}|{loc.get('postcode') or loc.get('city')}"
            if key not in seen:
                seen.add(key)
                locations.append(loc)

    logger.info(f"[gro-up-branches] {len(locations)} locations scraped")
    return locations


# ── Company configs ───────────────────────────────────────────────────────────

def scrape_2samen_vestigingen() -> list[dict]:
    """
    2Samen Kinderopvang (2samen.nl) — /kinderopvang listing page.
    Structure: <h3>Name</h3> <p>Street | Postcode</p> <p>City</p>
    """
    try:
        resp = requests.get(
            "https://www.2samen.nl/kinderopvang",
            headers=SCRAPER_HEADERS, timeout=20,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"[2samen-branches] listing mislukt: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    locations = []
    seen: set[str] = set()

    for h3 in soup.find_all("h3"):
        name = h3.get_text(strip=True)
        if not name or name.lower() in {"soort opvang", "filter", "locatie", "resultaten"}:
            continue

        # Collect next siblings until next h3
        p_texts = []
        for sib in h3.find_next_siblings():
            if sib.name == "h3":
                break
            text = sib.get_text(strip=True)
            if text:
                p_texts.append(text)

        if len(p_texts) < 2:
            continue

        # p_texts[0] = "Street | Postcode" (postcode may be truncated)
        # p_texts[1] = City
        address_raw = p_texts[0]
        city = p_texts[1]

        parts = [p.strip() for p in address_raw.split("|")]
        street = parts[0] if parts else ""
        pc_match = POSTCODE_RE.search(address_raw)
        postcode = pc_match.group(1).replace(" ", "") if pc_match else ""

        if not city or name in seen:
            continue
        seen.add(name)
        locations.append({
            "name": name, "street": street,
            "postcode": postcode, "city": city,
        })

    logger.info(f"[2samen-branches] {len(locations)} locations scraped")
    return locations


def scrape_mikz_vestigingen() -> list[dict]:
    """
    Mikz (mikz.nl) — embedded JS array App.locations on /locaties page.
    Structure: App.locations = [{coordinates: {...}, locations: [{name, address, city, postcode}]}]
    """
    import json as _json
    try:
        resp = requests.get(
            "https://www.mikz.nl/locaties",
            headers=SCRAPER_HEADERS, timeout=20,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"[mikz-branches] listing mislukt: {exc}")
        return []

    m = re.search(r"App\.locations\s*=\s*(\[.+?\]);\s*(?:App\.|$|//|\n)",
                  resp.text, re.DOTALL)
    if not m:
        logger.warning("[mikz-branches] App.locations niet gevonden")
        return []

    try:
        data = _json.loads(m.group(1))
    except Exception as exc:
        logger.warning(f"[mikz-branches] JSON parse mislukt: {exc}")
        return []

    locations = []
    seen: set[str] = set()
    for group in data:
        coords = group.get("coordinates", {})
        for loc in group.get("locations", []):
            name = loc.get("name", "").strip()
            street = loc.get("address", "").strip()
            city = loc.get("city", "").strip()
            postcode = loc.get("postcode", "").replace(" ", "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            entry: dict = {"name": name, "street": street, "postcode": postcode, "city": city}
            if coords.get("longitude") and coords.get("latitude"):
                entry["lon"] = coords["longitude"]
                entry["lat"] = coords["latitude"]
            locations.append(entry)

    logger.info(f"[mikz-branches] {len(locations)} locations scraped")
    return locations


def scrape_vlietkinderen_vestigingen() -> list[dict]:
    """
    Vlietkinderen (vlietkinderen.nl) — /locaties page.
    Addresses are in <span class="segment-post_code"> elements inside a
    flex container. The location name is in a h3/h4 ancestor.
    """
    try:
        resp = requests.get(
            "https://www.vlietkinderen.nl/locaties",
            headers=SCRAPER_HEADERS, timeout=20,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"[vlietkinderen-branches] listing mislukt: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    locations = []
    seen: set[str] = set()

    for pc_span in soup.find_all("span", class_="segment-post_code"):
        postcode_raw = pc_span.get_text(strip=True)
        pc_match = POSTCODE_RE.search(postcode_raw)
        if not pc_match:
            continue
        postcode = pc_match.group(1).replace(" ", "")

        # Address container is the parent div with street parts and postcode
        addr_div = pc_span.parent
        addr_text = addr_div.get_text(separator=" ", strip=True)
        m = POSTCODE_RE.search(addr_text)
        city = addr_text[m.end():].strip() if m else ""
        street_raw = addr_text[:m.start()].strip().rstrip(",").strip() if m else ""

        # Name: walk up to find h3/h4
        name = ""
        node = addr_div
        for _ in range(10):
            node = node.parent
            if node is None:
                break
            h = node.find("h3") or node.find("h4") or node.find("h2")
            if h:
                name = re.sub(r"^Welkom bij\s+", "", h.get_text(strip=True), flags=re.I)
                break

        if not name or not city or name in seen:
            continue
        seen.add(name)
        locations.append({
            "name": name, "street": street_raw,
            "postcode": postcode, "city": city,
        })

    logger.info(f"[vlietkinderen-branches] {len(locations)} locations scraped")
    return locations


def scrape_un1ek_vestigingen() -> list[dict]:
    """
    Un1ek Kinderopvang (un1ek.nl) — operates in 3 municipalities.
    API: /controllers/locaties/{tag} returns JSON with adres, postcode, plaatsnaam, cor_lat/cor_lng.
    Tags: kinderopvang, peuteropvang (for all types).
    """
    import json as _json
    base = "https://www.un1ek.nl/controllers/locaties"
    tags = ["kinderopvang", "peuteropvang", "buitenschoolse-opvang", "hele-dagopvang"]
    locations = []
    seen: set[str] = set()

    for tag in tags:
        try:
            resp = requests.get(
                f"{base}/{tag}",
                headers={**SCRAPER_HEADERS, "Accept": "application/json"},
                timeout=15,
            )
            if resp.status_code != 200 or not resp.text.strip():
                continue
            items = _json.loads(resp.text)
            if not isinstance(items, list):
                items = [items]
            for item in items:
                name = (item.get("naam") or "").strip()
                street = (item.get("adres") or "").strip()
                postcode = (item.get("postcode") or "").replace(" ", "").strip()
                city = (item.get("plaatsnaam") or "").strip()
                lon = item.get("cor_lng") or item.get("lon")
                lat = item.get("cor_lat") or item.get("lat")
                if not name or name in seen:
                    continue
                seen.add(name)
                entry: dict = {"name": name, "street": street, "postcode": postcode, "city": city}
                if lon and lat:
                    try:
                        entry["lon"] = float(lon)
                        entry["lat"] = float(lat)
                    except (TypeError, ValueError):
                        pass
                locations.append(entry)
        except Exception as exc:
            logger.debug(f"[un1ek-branches] tag={tag} failed: {exc}")

    logger.info(f"[un1ek-branches] {len(locations)} locations scraped")
    return locations


def scrape_bzzzonder_vestigingen() -> list[dict]:
    """
    Bzzzonder Kinderopvang (bzzzonder.nl) — locations in Amersfoort, Nijkerk, Ede, Voorthuizen.
    Scrapes /plekken/ for all location URLs, then each location page for address.
    Address format: 'Straatnaam 12, 1234AB Stad' in 'Adres gegevens' section.
    """
    import re as _re
    # street+number, postcode, city — city stops at @ (email), digit, or extra whitespace
    ADDR_RE = _re.compile(
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-\.]+?\s+\d{1,4}[a-zA-Z]{0,2}),?\s*"
        r"(\d{4}\s*[A-Z]{2})[,\s]+"
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{1,30}?)(?=[@\d]|\s{2,}|\s+en\s|$)"
    )
    plekken_url = "https://www.bzzzonder.nl/plekken/"
    locations = []

    try:
        resp = requests.get(plekken_url, headers=SCRAPER_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning(f"[bzzzonder-branches] Plekken pagina mislukt: {exc}")
        return []

    # Collect unique location page URLs
    loc_urls: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if (
            "/plekken/" in href
            and href != plekken_url
            and href not in seen
            and a.get_text(strip=True)
        ):
            seen.add(href)
            loc_urls.append(href)

    logger.info(f"[bzzzonder-branches] {len(loc_urls)} locatie-pagina's gevonden")

    for url in loc_urls:
        try:
            r = requests.get(url, headers=SCRAPER_HEADERS, timeout=15)
            r.raise_for_status()
            s = BeautifulSoup(r.text, "lxml")

            # Location name from H1
            h1 = s.find("h1")
            name = h1.get_text(strip=True) if h1 else url.rstrip("/").split("/")[-1]

            # Address from map-marker icon in 'Adres gegevens' section
            street = postcode = city = ""
            marker = s.select_one(".fa-map-marker-alt, .fa-map-marker")
            if marker:
                li = marker.find_parent("li")
                if li:
                    content = li.select_one(".fusion-li-item-content") or li
                    addr_text = content.get_text(strip=True)
                    m = ADDR_RE.search(addr_text)
                    if m:
                        street   = m.group(1).strip()
                        postcode = m.group(2).replace(" ", "").strip()
                        city     = m.group(3).strip()

            if not postcode:
                # Fallback: postcode from page text
                page_text = s.get_text(separator=" ")
                pc_m = _re.search(r"(\d{4}\s*[A-Z]{2})\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{2,20}(?:\s+[A-Z][A-Za-zÀ-ÿ\-]+)*)(?=[@\d\n\s])", page_text)
                if pc_m:
                    postcode = pc_m.group(1).replace(" ", "")
                    city     = pc_m.group(2).strip()

            if name:
                locations.append({
                    "name":     name,
                    "street":   street,
                    "postcode": postcode,
                    "city":     city,
                })
                logger.debug(f"[bzzzonder-branches] {name} — {street}, {postcode} {city}")
        except Exception as exc:
            logger.warning(f"[bzzzonder-branches] Locatie mislukt {url}: {exc}")

    logger.info(f"[bzzzonder-branches] {len(locations)} vestigingen gevonden")
    return locations


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
    "partou":     {"scraper": scrape_partou_vestigingen},
    "kinderdam":  {"scraper": scrape_kinderdam_vestigingen},
    "spring":     {"scraper": scrape_spring_vestigingen},
    "prokino":    {"scraper": scrape_prokino_vestigingen},
    "kober":      {"scraper": scrape_kober_vestigingen},
    "kion":       {"scraper": scrape_kion_vestigingen},
    "compananny": {"scraper": scrape_compananny_vestigingen},
    "sinne":      {"scraper": scrape_sinne_vestigingen},
    "tinteltuin": {"scraper": scrape_tinteltuin_vestigingen},
    "humankind":  {"scraper": scrape_humankind_vestigingen},
    # ── generic scrapers ──────────────────────────────────────────────────────
    "norlandia": {"scraper": scrape_norlandia_vestigingen},
    "gro-up": {"scraper": scrape_gro_up_vestigingen},
    "kibeo": _generic(
        "kibeo",
        "https://www.kibeo.nl",
    ),
    "kindergarden": {"scraper": scrape_kindergarden_vestigingen},
    "bijdehandjes": {"scraper": scrape_bijdehandjes_vestigingen},
    "bink": _generic(
        "bink",
        "https://www.debinkopmeer.nl",     # binkopvang.nl redirects here
    ),
    "dak": {"scraper": scrape_dak_vestigingen},
    "dichtbij": _generic(
        "dichtbij",
        "https://www.dichtbijkinderopvang.nl",
        "https://www.kdv-dichtbij.nl",
    ),
    "kinderwoud": _generic(
        "kinderwoud",
        "https://www.kinderwoud.nl",
    ),
    "kids-first": _generic(
        "kids-first",
        "https://www.kidsfirst.nl",            # .nl works; kidsfirstkinderopvang.nl has DNS issues
        "https://www.kidsfirstkinderopvang.nl",
    ),
    "mik": {"scraper": scrape_mik_vestigingen},    # mik-nijmegen.nl → mik-spelenderwijs.nl
    "op-stoom": _generic(
        "op-stoom",
        "https://www.op-stoom.nl",
    ),
    "ska": _generic(
        "ska",
        "https://www.ska.nl",
    ),
    "2samen": {"scraper": scrape_2samen_vestigingen},
    "mikz":   {"scraper": scrape_mikz_vestigingen},
    "vlietkinderen": {"scraper": scrape_vlietkinderen_vestigingen},
    "un1ek":  {"scraper": scrape_un1ek_vestigingen},
    "wasko":       {"scraper": scrape_wasko_vestigingen},
    "wij-zijn-jong": {"scraper": scrape_wij_zijn_jong_vestigingen},
    "kanteel":     {"scraper": scrape_kanteel_vestigingen},
    "ko-walcheren": {"scraper": scrape_ko_walcheren_vestigingen},
    "bzzzonder":    {"scraper": scrape_bzzzonder_vestigingen},
    "samenwerkende-ko": _generic(
        "samenwerkende-ko",
        "https://www.samenwerkendekinderopvang.nl",
    ),
}


# ── Main run function ─────────────────────────────────────────────────────────

def _locations_from_jobs(cur, company_slug: str) -> list[dict]:
    """
    Fallback: derive locations from already-scraped job data.

    When the branch scraper finds nothing (site is AJAX-only, DNS dead, etc.),
    we extract distinct location_name values from jobs stored for that company.
    These are geocoded via PDOK and saved as approximate branches.

    Only location_names with a valid postcode or city are usable.
    """
    # Map company slug → company name in jobs table (slug matches Company.slug)
    cur.execute("""
        SELECT DISTINCT j.location_name, j.city, j.postcode
        FROM   jobs_job     j
        JOIN   jobs_company c ON c.id = j.company_id
        WHERE  c.slug        = %s
          AND  j.is_expired  = FALSE
          AND  j.location_name <> ''
        ORDER  BY j.location_name
    """, (company_slug,))
    rows = cur.fetchall()
    if not rows:
        return []

    locations = []
    seen: set[str] = set()
    for location_name, city, postcode in rows:
        pc = (postcode or "").replace(" ", "").upper()
        if not POSTCODE_RE.match(pc):
            pc = ""
        city = (city or "").strip()
        key = f"{location_name}|{pc or city}"
        if key in seen or not (pc or city):
            continue
        seen.add(key)
        locations.append({
            "name": location_name,
            "street": "",
            "postcode": pc,
            "city": city,
        })

    logger.info(f"[branches] {company_slug}: {len(locations)} locations from job data (fallback)")
    return locations


def _parallel_geocode(locations_needing_geo: list[tuple]) -> None:
    """
    Geocode a list of (loc_dict, query_string) pairs in parallel.

    Updates loc_dict in-place with lon/lat/city/postcode from PDOK.
    Uses a semaphore to stay polite (max 5 concurrent PDOK requests).
    """
    if not locations_needing_geo:
        return

    _sem = threading.Semaphore(5)

    def _geo_one(item):
        loc, query = item
        with _sem:
            result = _geocode_via_pdok(query)
        if result:
            loc["lon"] = result["lon"]
            loc["lat"] = result["lat"]
            if not loc.get("city"):
                loc["city"] = result.get("city", "")
            if not loc.get("postcode"):
                loc["postcode"] = result.get("postcode", "")

    logger.info(f"[branches] Geocoding {len(locations_needing_geo)} locations in parallel...")
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(_geo_one, locations_needing_geo))


def run_vestigingen_scrape(company_slugs: list[str] | None = None) -> dict:
    """
    Scrape branches for the given companies (or all if None).

    Geoptimaliseerde pipeline:
      1. Alle company scrapers parallel uitvoeren (ThreadPoolExecutor, 8 workers)
      2. DB-fallback voor bedrijven zonder resultaat
      3. PDOK geocoding parallel uitvoeren (5 workers, semaphore)
      4. Alle locaties batch-upserten naar de DB
      5. Bestaande jobs verrijken met vestiging-adressen

    Geeft per-bedrijf statistieken terug.
    """
    if company_slugs is None:
        company_slugs = list(COMPANY_CONFIGS.keys())

    # ── Stap 1: Scrapers parallel uitvoeren ───────────────────────────────────

    # Valideer slugs vóór parallel uitvoering
    known_slugs = [s for s in company_slugs if COMPANY_CONFIGS.get(s)]
    for slug in company_slugs:
        if slug not in COMPANY_CONFIGS:
            logger.warning(f"[branches] No config for '{slug}'")

    def _run_scraper(slug):
        try:
            return slug, COMPANY_CONFIGS[slug]["scraper"](), None
        except Exception as exc:
            logger.error(f"[branches] {slug} scraper error: {exc}")
            return slug, [], str(exc)

    logger.info(f"[branches] Scraping {len(known_slugs)} companies in parallel...")
    scraper_results: dict[str, tuple] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for slug, locs, err in pool.map(_run_scraper, known_slugs):
            scraper_results[slug] = (locs, err)

    # ── Stap 2–4: DB-fallback, geocoding, upserts ─────────────────────────────

    conn = get_connection()
    stats: dict = {}

    try:
        with conn:
            cur = conn.cursor()

            # DB-fallback voor bedrijven zonder scraped locations
            fallback_flags: dict[str, bool] = {}
            for slug in known_slugs:
                locs, err = scraper_results[slug]
                if err and not locs:
                    stats[slug] = {"error": err, "locations": 0, "fallback": False}
                if not locs:
                    fb = _locations_from_jobs(cur, slug)
                    scraper_results[slug] = (fb, err)
                    fallback_flags[slug] = bool(fb)
                else:
                    fallback_flags[slug] = False

            # Verzamel locaties die PDOK geocoding nodig hebben
            to_geocode: list[tuple] = []
            for slug in known_slugs:
                locs, _ = scraper_results[slug]
                for loc in locs:
                    if loc.get("lon") is None:
                        street = loc.get("street", "")
                        postcode = loc.get("postcode", "")
                        city = loc.get("city", "")
                        name = loc.get("name", "")
                        if street and postcode and city:
                            query = f"{street}, {postcode} {city}"
                        elif postcode and city:
                            query = f"{postcode} {city}"
                        elif city:
                            query = city
                        else:
                            query = name
                        if query:
                            to_geocode.append((loc, query))

            _parallel_geocode(to_geocode)

            # Upserts naar DB
            for slug in known_slugs:
                locs, err = scraper_results[slug]
                fallback_used = fallback_flags.get(slug, False)

                inserted = 0
                for loc in locs:
                    cur.execute("SAVEPOINT sp_upsert")
                    try:
                        upsert_vestiging(
                            cur,
                            company_slug=slug,
                            name=loc["name"],
                            street=loc.get("street", ""),
                            postcode=loc.get("postcode", ""),
                            city=loc.get("city", ""),
                            lon=loc.get("lon"),
                            lat=loc.get("lat"),
                        )
                        cur.execute("RELEASE SAVEPOINT sp_upsert")
                        inserted += 1
                    except Exception as exc:
                        cur.execute("ROLLBACK TO SAVEPOINT sp_upsert")
                        logger.warning(f"[branches] Upsert failed for {loc.get('name')}: {exc}")

                if "error" not in stats.get(slug, {}):
                    stats[slug] = {"locations": inserted, "fallback": fallback_used}
                else:
                    stats[slug]["locations"] = inserted
                    stats[slug]["fallback"] = fallback_used
                logger.info(
                    f"[branches] {slug}: {inserted} branches saved"
                    + (" (from job data)" if fallback_used else "")
                )

        # ── Stap 5: Verrijk bestaande jobs ────────────────────────────────────
        enriched = _enrich_existing_jobs(conn)
        logger.info(f"[branches] {enriched} bestaande jobs verrijkt met vestiging-adres")
        stats["_enriched_jobs"] = enriched

    finally:
        conn.close()

    return stats


def _enrich_existing_jobs(conn) -> int:
    """
    Update bestaande jobs zonder straat/postcode op basis van vestiging-data.
    Wordt aangeroepen na run_vestigingen_scrape zodat verse branch-data meteen
    doorvloeit naar de bijbehorende vacatures.

    Optmalisaties t.o.v. de vorige versie:
      - Één cursor hergebruikt voor alle match_vestiging queries
      - Één cursor hergebruikt voor alle UPDATE queries
      - Geen extra `with conn.cursor()` overhead per job
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT j.id, c.slug, j.location_name, j.city, j.title
            FROM jobs_job j
            JOIN jobs_company c ON c.id = j.company_id
            WHERE j.is_active = TRUE
              AND (j.street IS NULL OR j.street = '')
        """)
        jobs = cur.fetchall()

        updates: list[tuple] = []
        for job_id, company_slug, loc_name, city, title in jobs:
            v = match_vestiging(cur, company_slug, loc_name or "", city or "", title or "")
            if v and (v.get("street") or v.get("postcode")):
                updates.append((
                    v.get("street", ""),
                    v.get("postcode", ""),
                    v.get("city", "") or city or "",
                    v.get("lon"),
                    v.get("lat"),
                    job_id,
                ))

        if not updates:
            return 0

        for street, postcode, city, lon, lat, job_id in updates:
            cur.execute("""
                UPDATE jobs_job SET
                    street    = CASE WHEN %s != '' THEN %s ELSE street END,
                    postcode  = CASE WHEN %s != '' THEN %s ELSE postcode END,
                    city      = CASE WHEN %s != '' THEN %s ELSE city END,
                    location  = CASE WHEN %s IS NOT NULL
                                     THEN ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                                     ELSE location END,
                    updated_at = NOW()
                WHERE id = %s
            """, (street, street, postcode, postcode, city, city,
                  lon, lon, lat, job_id))

    conn.commit()
    return len(updates)
