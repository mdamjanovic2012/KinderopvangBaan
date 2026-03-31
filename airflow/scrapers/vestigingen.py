"""
Vestigingen scraper — haalt precieze adressen op van kinderopvang locaties.

Probleem: job listings vermelden alleen een stad ("Rotterdam") maar PDOK geocodeert
dat naar het stadscentrum. Alle Rotterdamse vacatures krijgen dan dezelfde coördinaten.

Oplossing: scrape de "vestigingen/locaties" pagina van het hoofdbedrijfswebsite
(NIET de job board), bewaar naam + volledig adres in jobs_vestiging, en gebruik
die precieze coördinaten als fallback bij job geocoding.

Matching strategie:
  1. Exacte naam match: location_name == vestiging.name → precieze coördinaten
  2. Stad match (alleen 1 vestiging in die stad): city == vestiging.city → precieze coördinaten
  3. Fallback: bestaand stad-niveau geocoding (ongewijzigd)

Ondersteunde bedrijven:
  - Partou       (partou.nl/kinderopvang/vestigingen)
  - Kinderdam    (kinderdam.nl/locaties)
  - Spring       (spring-kinderopvang.nl/vestigingen)
  - Prokino      (prokino.nl - scrapes company site, not job board)
  - Norlandia    (norlandia.nl/kinderopvang/vestigingen)
  - Gro-up       (gro-up.nl/locaties)
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

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs_vestiging (
    id          SERIAL PRIMARY KEY,
    company_slug VARCHAR(100) NOT NULL,
    name        VARCHAR(300) NOT NULL,
    street      VARCHAR(200) DEFAULT '',
    postcode    VARCHAR(10)  DEFAULT '',
    city        VARCHAR(100) NOT NULL,
    location    GEOGRAPHY(POINT, 4326),
    geocoded_at TIMESTAMP,
    scraped_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_slug, name)
);
"""


def ensure_table(cur) -> None:
    cur.execute(CREATE_TABLE_SQL)


def upsert_vestiging(cur, company_slug: str, name: str, street: str,
                     postcode: str, city: str) -> None:
    """Upsert een vestiging record. Geocodeert als locatie ontbreekt."""
    # Geocode best available address
    query = ""
    if street and postcode and city:
        query = f"{street}, {postcode} {city}"
    elif postcode and city:
        query = f"{postcode} {city}"
    elif city:
        query = city

    lon = lat = geocoded_at_expr = None
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
                (company_slug, name, street, postcode, city, location, geocoded_at, scraped_at)
            VALUES (%s, %s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    NOW(), NOW())
            ON CONFLICT (company_slug, name) DO UPDATE SET
                street      = EXCLUDED.street,
                postcode    = EXCLUDED.postcode,
                city        = EXCLUDED.city,
                location    = EXCLUDED.location,
                geocoded_at = EXCLUDED.geocoded_at,
                scraped_at  = EXCLUDED.scraped_at
        """, (company_slug, name, street, postcode, city, lon, lat))
    else:
        cur.execute("""
            INSERT INTO jobs_vestiging
                (company_slug, name, street, postcode, city, scraped_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (company_slug, name) DO UPDATE SET
                street     = EXCLUDED.street,
                postcode   = EXCLUDED.postcode,
                city       = EXCLUDED.city,
                scraped_at = EXCLUDED.scraped_at
        """, (company_slug, name, street, postcode, city))


def match_vestiging(cur, company_slug: str, location_name: str, city: str) -> dict | None:
    """
    Zoek precieze vestiging-coördinaten voor een vacature.
    Geeft {lon, lat, postcode, city} of None terug.
    """
    # 1. Exacte naam match
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

        # Partial name match (vestiging name contains location_name or vice versa)
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

    # 2. Stad match — alleen als er precies 1 vestiging in die stad is
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

    return None


# ── Generic address extraction ────────────────────────────────────────────────

def _extract_address_from_element(el) -> tuple[str, str, str]:
    """
    Probeer naam, straat, postcode+stad te extraheren uit een BeautifulSoup element.
    Geeft (name, street, postcode_city) terug.
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
    Parseer adres uit vrije tekst. Geeft (street, postcode, city) terug.
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


# ── Company-specific scrapers ─────────────────────────────────────────────────

def scrape_partou_vestigingen() -> list[dict]:
    """
    Scrapt Partou vestigingen van partou.nl.
    Partou gebruikt een React/Next.js website met een locatiefinder.
    Probeert JSON data en fallback HTML scraping.
    """
    locations = []
    BASE = "https://www.partou.nl"

    # Probeer de vestigingen overview pagina
    for path in ["/kinderopvang/vestigingen", "/vestigingen", "/locaties"]:
        url = BASE + path
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Schema.org LocalBusiness / ChildCare
            for ld in soup.find_all("script", type="application/ld+json"):
                import json
                try:
                    data = json.loads(ld.string or "")
                    if isinstance(data, list):
                        data = data
                    else:
                        data = [data]
                    for item in data:
                        if item.get("@type") in ("ChildCare", "LocalBusiness", "Organization"):
                            addr = item.get("address", {})
                            name = item.get("name", "")
                            street = addr.get("streetAddress", "")
                            postcode = addr.get("postalCode", "").replace(" ", "")
                            city = addr.get("addressLocality", "")
                            if name and city:
                                locations.append({
                                    "name": name,
                                    "street": street,
                                    "postcode": postcode,
                                    "city": city,
                                })
                except Exception:
                    pass

            # HTML fallback: zoek adresblokken
            if not locations:
                for card in soup.select("[class*='location'], [class*='vestiging'], [class*='locatie']"):
                    name_el = card.select_one("h2, h3, h4, [class*='title'], [class*='name']")
                    name = name_el.get_text(strip=True) if name_el else ""
                    addr_el = card.select_one("[class*='address'], address, p")
                    if name and addr_el:
                        street, postcode, city = _parse_address_block(addr_el.get_text())
                        if city:
                            locations.append({
                                "name": name,
                                "street": street,
                                "postcode": postcode,
                                "city": city,
                            })

            if locations:
                logger.info(f"[partou-vestigingen] {len(locations)} locaties gevonden op {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[partou-vestigingen] {url} mislukt: {exc}")

    logger.warning("[partou-vestigingen] Geen locaties gevonden")
    return locations


def scrape_kinderdam_vestigingen() -> list[dict]:
    """
    Scrapt Kinderdam vestigingen van kinderdam.nl.
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

            # Schema.org
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

            # HTML: zoek kaarten met naam + adres
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
                logger.info(f"[kinderdam-vestigingen] {len(locations)} locaties op {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[kinderdam-vestigingen] {url} mislukt: {exc}")

    return locations


def _scrape_generic_vestigingen(company_slug: str, base_url: str,
                                 location_paths: list[str]) -> list[dict]:
    """
    Generieke vestigingen scraper voor bedrijven met een standaard locatiepagina.
    Probeert schema.org JSON-LD, dan HTML kaarten.
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

            # JSON-LD
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

            # HTML fallback
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
                logger.info(f"[{company_slug}-vestigingen] {len(locations)} locaties op {url}")
                return locations

        except Exception as exc:
            logger.warning(f"[{company_slug}-vestigingen] {url} mislukt: {exc}")

    return locations


# ── Company configs ───────────────────────────────────────────────────────────

COMPANY_CONFIGS = {
    "partou": {
        "scraper": scrape_partou_vestigingen,
    },
    "kinderdam": {
        "scraper": scrape_kinderdam_vestigingen,
    },
    "spring": {
        "scraper": lambda: _scrape_generic_vestigingen(
            "spring", "https://www.spring-kinderopvang.nl",
            ["/vestigingen", "/locaties", "/onze-locaties"],
        ),
    },
    "prokino": {
        "scraper": lambda: _scrape_generic_vestigingen(
            "prokino", "https://www.prokino.nl",
            ["/locaties", "/vestigingen", "/kinderopvang"],
        ),
    },
    "norlandia": {
        "scraper": lambda: _scrape_generic_vestigingen(
            "norlandia", "https://www.norlandia.nl",
            ["/kinderopvang/vestigingen", "/vestigingen", "/locaties"],
        ),
    },
    "gro-up": {
        "scraper": lambda: _scrape_generic_vestigingen(
            "gro-up", "https://www.gro-up.nl",
            ["/locaties", "/vestigingen", "/kinderopvang/locaties"],
        ),
    },
}


# ── Main run function ─────────────────────────────────────────────────────────

def run_vestigingen_scrape(company_slugs: list[str] | None = None) -> dict:
    """
    Scrapt vestigingen voor de opgegeven bedrijven (of alle als None).
    Geocodeert en bewaart in jobs_vestiging tabel.
    Geeft statistieken terug.
    """
    if company_slugs is None:
        company_slugs = list(COMPANY_CONFIGS.keys())

    conn = get_connection()
    stats = {}

    try:
        with conn:
            cur = conn.cursor()
            ensure_table(cur)

            for slug in company_slugs:
                config = COMPANY_CONFIGS.get(slug)
                if not config:
                    logger.warning(f"[vestigingen] Geen config voor '{slug}'")
                    continue

                logger.info(f"[vestigingen] Scraping {slug}...")
                try:
                    locations = config["scraper"]()
                except Exception as exc:
                    logger.error(f"[vestigingen] {slug} scraper fout: {exc}")
                    stats[slug] = {"error": str(exc)}
                    continue

                inserted = updated = 0
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
                        logger.warning(f"[vestigingen] Upsert mislukt voor {loc.get('name')}: {exc}")

                stats[slug] = {"locations": inserted}
                logger.info(f"[vestigingen] {slug}: {inserted} vestigingen opgeslagen")

    finally:
        conn.close()

    return stats
