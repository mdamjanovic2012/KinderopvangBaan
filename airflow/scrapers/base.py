"""
BaseScraper — basis voor alle job scrapers.

Aanpak:
1. fetch_company()  → subclass scrapet bedrijfsinfo (eenmalig / idempotent)
2. fetch_jobs()     → subclass haalt vacatures op van website
3. geocode()        → PDOK geocoding met DB-cache (jobs_geocodedlocation)
4. reconcile()      → vergelijk scraped vs. DB, apply changes in transactie
5. validatie        → rollback als actieve jobs > 30% dalen (scraper-fout)

Bedrijfsinfo wordt alleen bijgewerkt als het nieuw is of als logo/website veranderd is.
"""

import logging
import re
import requests
from datetime import datetime, timezone

from db.connection import get_connection

logger = logging.getLogger(__name__)

PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"

SCRAPER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9",
}


# ── PDOK geocoding ────────────────────────────────────────────────────────────

def _geocode_via_pdok(location_name: str) -> dict | None:
    """Roep PDOK Locatieserver aan. Geeft {city, postcode, municipality, lon, lat} of None."""
    try:
        resp = requests.get(
            PDOK_URL,
            params={
                "q": location_name,
                "fq": "bron:BAG",
                "rows": 1,
                "fl": "centroide_ll,woonplaatsnaam,postcode,gemeentenaam",
            },
            timeout=10,
        )
        resp.raise_for_status()
        docs = resp.json().get("response", {}).get("docs", [])
        if not docs:
            return None

        doc = docs[0]
        m = re.search(r"POINT\(([\d.]+)\s+([\d.]+)\)", doc.get("centroide_ll", ""))
        if not m:
            return None

        return {
            "lon": float(m.group(1)),
            "lat": float(m.group(2)),
            "city": doc.get("woonplaatsnaam", ""),
            "postcode": doc.get("postcode", ""),
            "municipality": doc.get("gemeentenaam", ""),
        }
    except Exception as exc:
        logger.warning(f"PDOK geocoding mislukt voor '{location_name}': {exc}")
        return None


def geocode_locations(cur, location_names: set[str]) -> dict[str, dict]:
    """
    Geocode een set locatienamen. Raadpleegt eerst de DB-cache (jobs_geocodedlocation),
    daalt dan terug op PDOK voor onbekende namen.
    Geeft {location_name: {lon, lat, city, postcode, municipality}} terug.
    """
    if not location_names:
        return {}

    # Haal cache op uit DB
    cur.execute(
        "SELECT location_name, city, postcode, municipality, "
        "ST_X(location::geometry) AS lon, ST_Y(location::geometry) AS lat "
        "FROM jobs_geocodedlocation WHERE location_name = ANY(%s)",
        (list(location_names),)
    )
    cache = {}
    for row in cur.fetchall():
        name, city, postcode, municipality, lon, lat = row
        cache[name] = {"city": city, "postcode": postcode, "municipality": municipality,
                       "lon": lon, "lat": lat}

    # Geocode ontbrekende namen via PDOK
    missing = location_names - set(cache.keys())
    logger.info(f"Geocoding: {len(cache)} uit cache, {len(missing)} via PDOK")

    for name in missing:
        geo = _geocode_via_pdok(name)
        if not geo:
            continue
        cache[name] = geo
        # Sla op in cache
        cur.execute(
            """
            INSERT INTO jobs_geocodedlocation
                (location_name, city, postcode, municipality, location, geocoded_at)
            VALUES (%s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    NOW())
            ON CONFLICT (location_name) DO NOTHING
            """,
            (name, geo["city"], geo["postcode"], geo["municipality"], geo["lon"], geo["lat"]),
        )

    return cache


# ── BaseScraper ───────────────────────────────────────────────────────────────

class BaseScraper:
    """
    Subclass implementeert fetch_company() en fetch_jobs().
    run() regelt de volledige staging/reconcile/commit cyclus.
    """

    company_slug: str = ""  # moet overeenkomen met jobs_company.slug in DB

    def fetch_company(self) -> dict:
        """
        Scrapet bedrijfsinfo van de website. Geeft dict terug:
        {
            name*,          # officiële bedrijfsnaam
            website*,       # hoofdwebsite (bijv. https://www.kinderdam.nl)
            job_board_url*, # URL van de vacaturepagina
            scraper_class*, # naam van deze klasse
            logo_url,       # URL van het logo (uit header/footer)
            description,    # korte bedrijfsbeschrijving (optioneel)
        }
        Wordt eenmalig gebruikt bij eerste scrape; daarna alleen logo/website bijgewerkt.
        """
        raise NotImplementedError

    def fetch_jobs(self) -> list[dict]:
        """
        Haalt vacatures op van de website. Geeft lijst van dicts terug:
        {
            source_url*,        # unieke URL van de vacature (verplicht)
            external_id,        # ID van de website zelf (optioneel)
            title*,             # vacaturetitel (verplicht)
            short_description,  # korte samenvatting
            description,        # volledige omschrijving
            location_name,      # naam van de opvanglocatie
            city,               # fallback als geocoding mislukt
            salary_min/max,     # Decimal of None
            hours_min/max,      # int of None
            age_min/max,        # int of None
            contract_type,      # fulltime / parttime / temp / ""
            job_type,           # CAO functietype of ""
        }
        """
        raise NotImplementedError

    def _upsert_company(self, cur, company_data: dict) -> int:
        """
        Maakt een nieuw Company record aan of werkt logo/website bij.
        Geeft company_id terug.
        """
        cur.execute("SELECT id, logo_url, website FROM jobs_company WHERE slug = %s", (self.company_slug,))
        row = cur.fetchone()

        if row:
            company_id, existing_logo, existing_website = row
            new_logo = company_data.get("logo_url", "")
            new_website = company_data.get("website", "")
            new_desc = company_data.get("description", "")
            if (new_logo and new_logo != existing_logo) or (new_website and new_website != existing_website):
                cur.execute(
                    """UPDATE jobs_company
                       SET logo_url = %s, website = %s, description = COALESCE(NULLIF(%s,''), description),
                           updated_at = NOW()
                       WHERE id = %s""",
                    (new_logo or existing_logo, new_website or existing_website, new_desc, company_id),
                )
                logger.info(f"[{self.company_slug}] Bedrijfsinfo bijgewerkt")
            else:
                logger.info(f"[{self.company_slug}] Bedrijf al bekend, geen wijzigingen")
            return company_id
        else:
            cur.execute(
                """
                INSERT INTO jobs_company
                    (name, slug, website, job_board_url, scraper_class, logo_url, description, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                RETURNING id
                """,
                (
                    company_data["name"],
                    self.company_slug,
                    company_data.get("website", ""),
                    company_data.get("job_board_url", ""),
                    company_data.get("scraper_class", self.__class__.__name__),
                    company_data.get("logo_url", ""),
                    company_data.get("description", ""),
                ),
            )
            company_id = cur.fetchone()[0]
            logger.info(f"[{self.company_slug}] Nieuw bedrijf aangemaakt: id={company_id}")
            return company_id

    def run(self) -> dict:
        """
        Volledige scrape-run:
        1. Haal jobs op
        2. Geocode locaties
        3. Reconcile met DB in één transactie
        4. Valideer (rollback als jobs > 30% dalen)
        """
        logger.info(f"[{self.company_slug}] === Start scrape run ===")

        jobs = self.fetch_jobs()
        logger.info(f"[{self.company_slug}] Gescraped: {len(jobs)} vacatures")

        if not jobs:
            logger.warning(f"[{self.company_slug}] Geen vacatures gevonden — scrape overgeslagen")
            return {"inserted": 0, "updated": 0, "expired": 0, "skipped": True}

        conn = get_connection()
        try:
            with conn:
                cur = conn.cursor()

                # Bedrijfsinfo ophalen en upserten (eenmalig of bij wijziging)
                company_data = self.fetch_company()
                company_id = self._upsert_company(cur, company_data)

                # Geocode unieke locaties
                unique_locations = {j["location_name"] for j in jobs if j.get("location_name")}
                geo_cache = geocode_locations(cur, unique_locations)

                # Huidige actieve source_urls in DB
                cur.execute(
                    "SELECT source_url FROM jobs_job WHERE company_id = %s AND is_expired = FALSE",
                    (company_id,)
                )
                current_urls = {r[0] for r in cur.fetchall()}
                scraped_urls = {j["source_url"] for j in jobs if j.get("source_url")}

                # Markeer verlopen jobs
                expired_urls = current_urls - scraped_urls
                if expired_urls:
                    cur.execute(
                        "UPDATE jobs_job SET is_expired = TRUE, is_active = FALSE, updated_at = NOW() "
                        "WHERE company_id = %s AND source_url = ANY(%s)",
                        (company_id, list(expired_urls)),
                    )
                    logger.info(f"[{self.company_slug}] Verlopen: {len(expired_urls)}")

                # Upsert jobs
                inserted = updated = 0
                now = datetime.now(timezone.utc)

                for job in jobs:
                    source_url = job.get("source_url", "").strip()
                    if not source_url:
                        continue

                    loc_name = job.get("location_name", "")
                    geo = geo_cache.get(loc_name, {})
                    city = geo.get("city") or job.get("city", "")
                    postcode = geo.get("postcode", "")
                    lon = geo.get("lon")
                    lat = geo.get("lat")

                    params = {
                        "company_id": company_id,
                        "title": job.get("title", ""),
                        "short_description": job.get("short_description", ""),
                        "description": job.get("description", ""),
                        "location_name": loc_name,
                        "city": city,
                        "postcode": postcode,
                        "lon": lon,
                        "lat": lat,
                        "salary_min": job.get("salary_min"),
                        "salary_max": job.get("salary_max"),
                        "hours_min": job.get("hours_min"),
                        "hours_max": job.get("hours_max"),
                        "age_min": job.get("age_min"),
                        "age_max": job.get("age_max"),
                        "contract_type": job.get("contract_type", ""),
                        "job_type": job.get("job_type", ""),
                        "source_url": source_url,
                        "external_id": job.get("external_id", ""),
                        "now": now,
                    }

                    if source_url in current_urls:
                        cur.execute(
                            """
                            UPDATE jobs_job SET
                                title            = %(title)s,
                                short_description= %(short_description)s,
                                description      = %(description)s,
                                location_name    = %(location_name)s,
                                city             = %(city)s,
                                postcode         = %(postcode)s,
                                location         = CASE
                                                     WHEN %(lon)s IS NOT NULL
                                                     THEN ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
                                                     ELSE location
                                                   END,
                                salary_min       = %(salary_min)s,
                                salary_max       = %(salary_max)s,
                                hours_min        = %(hours_min)s,
                                hours_max        = %(hours_max)s,
                                age_min          = %(age_min)s,
                                age_max          = %(age_max)s,
                                contract_type    = %(contract_type)s,
                                job_type         = %(job_type)s,
                                last_seen_at     = %(now)s,
                                is_expired       = FALSE,
                                is_active        = TRUE,
                                updated_at       = %(now)s
                            WHERE source_url = %(source_url)s AND company_id = %(company_id)s
                            """,
                            params,
                        )
                        updated += 1
                    else:
                        cur.execute(
                            """
                            INSERT INTO jobs_job (
                                company_id, title, short_description, description,
                                location_name, city, postcode, location,
                                salary_min, salary_max, hours_min, hours_max,
                                age_min, age_max, contract_type, job_type,
                                source_url, external_id, last_seen_at,
                                is_expired, is_active, is_premium,
                                requires_vog, requires_diploma, requires_bevoegdheid,
                                min_experience, created_at, updated_at
                            ) VALUES (
                                %(company_id)s, %(title)s, %(short_description)s, %(description)s,
                                %(location_name)s, %(city)s, %(postcode)s,
                                CASE WHEN %(lon)s IS NOT NULL
                                     THEN ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
                                     ELSE NULL END,
                                %(salary_min)s, %(salary_max)s, %(hours_min)s, %(hours_max)s,
                                %(age_min)s, %(age_max)s, %(contract_type)s, %(job_type)s,
                                %(source_url)s, %(external_id)s, %(now)s,
                                FALSE, TRUE, FALSE,
                                TRUE, FALSE, '[]',
                                NULL, %(now)s, %(now)s
                            )
                            """,
                            params,
                        )
                        inserted += 1

                # Validatie: actieve jobs mogen niet > 30% dalen
                cur.execute(
                    "SELECT COUNT(*) FROM jobs_job WHERE company_id = %s AND is_expired = FALSE",
                    (company_id,)
                )
                new_count = cur.fetchone()[0]
                old_count = len(current_urls)

                if old_count > 10 and new_count < old_count * 0.70:
                    raise ValueError(
                        f"[{self.company_slug}] VEILIGHEID: jobs daalden van {old_count} "
                        f"naar {new_count} (>30%). Transactie teruggedraaid."
                    )

                # Tijdstempel bijwerken
                cur.execute(
                    "UPDATE jobs_company SET last_scraped_at = NOW() WHERE slug = %s",
                    (self.company_slug,)
                )

                stats = {"inserted": inserted, "updated": updated, "expired": len(expired_urls)}
                logger.info(f"[{self.company_slug}] Klaar: {stats}")
                return stats

        finally:
            conn.close()
