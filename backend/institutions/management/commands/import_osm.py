"""
Fetches childcare institutions from OpenStreetMap via Overpass API
and imports them directly into the database.

Splits the Netherlands into regions to avoid Overpass timeout.

Usage:
    python manage.py import_osm
    python manage.py import_osm --clear
"""
import logging
import time
import requests
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from institutions.models import Institution

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Split NL into 6 horizontal slices to avoid timeout
NL_REGIONS = [
    ("Noord-Nederland",    "52.8,3.35,53.55,7.22"),
    ("Oost-Nederland",     "52.0,5.5,52.8,7.22"),
    ("West-Nederland-N",   "52.0,3.35,52.8,5.5"),
    ("Midden-Nederland",   "51.5,3.35,52.0,6.5"),
    ("Zuid-Nederland-W",   "50.75,3.35,51.5,5.0"),
    ("Zuid-Nederland-O",   "50.75,5.0,51.5,6.5"),
]


def make_query(bbox):
    return f"""
[out:json][timeout:60];
(
  node[amenity=kindergarten]({bbox});
  way[amenity=kindergarten]({bbox});
  node[amenity=childcare]({bbox});
  way[amenity=childcare]({bbox});
);
out center;
"""


def guess_type(tags):
    name = (tags.get("name") or "").lower()
    operator = (tags.get("operator") or "").lower()
    combined = name + " " + operator
    if any(k in combined for k in ["bso", "buitenschoolse"]):
        return Institution.TYPE_BSO
    if any(k in combined for k in ["gastouder", "gastouderbureau"]):
        return Institution.TYPE_GASTOUDER
    if any(k in combined for k in ["peuterspeelzaal", "peuteropvang", "peuter"]):
        return Institution.TYPE_PEUTERSPEELZAAL
    return Institution.TYPE_KDV


def extract_city(tags):
    return (
        tags.get("addr:city")
        or tags.get("addr:town")
        or tags.get("addr:village")
        or tags.get("addr:municipality")
        or ""
    )


class Command(BaseCommand):
    help = "Import NL childcare institutions from OpenStreetMap"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true",
                            help="Delete all existing institutions before import")

    def handle(self, *args, **options):
        if options["clear"]:
            count = Institution.objects.count()
            Institution.objects.all().delete()
            self.stdout.write(f"Cleared {count} existing institutions.")

        total_created = total_updated = total_skipped = 0

        for region_name, bbox in NL_REGIONS:
            self.stdout.write(f"\nFetching {region_name}...")

            for attempt in range(3):
                try:
                    resp = requests.post(
                        OVERPASS_URL,
                        data={"data": make_query(bbox)},
                        timeout=90,
                    )
                    resp.raise_for_status()
                    elements = resp.json().get("elements", [])
                    break
                except (requests.RequestException, ValueError, KeyError) as exc:
                    if attempt < 2:
                        self.stdout.write(f"  Retry {attempt + 1}/3 ({exc})")
                        time.sleep(10)
                    else:
                        self.stderr.write(self.style.WARNING(f"  Skipped {region_name}: {exc}"))
                        elements = []

            self.stdout.write(f"  {len(elements)} elements received")
            created = updated = skipped = 0

            for elem in elements:
                tags = elem.get("tags", {})
                name = tags.get("name", "").strip()
                if not name:
                    skipped += 1
                    continue

                country = tags.get("addr:country", "NL")
                if country and country != "NL":
                    skipped += 1
                    continue

                if elem["type"] == "node":
                    lat, lng = elem.get("lat"), elem.get("lon")
                else:
                    center = elem.get("center", {})
                    lat, lng = center.get("lat"), center.get("lon")

                if not lat or not lng:
                    skipped += 1
                    continue

                osm_id = f"osm_{elem['type']}_{elem['id']}"

                _, flag = Institution.objects.update_or_create(
                    lrk_number=osm_id,
                    defaults={
                        "name": name,
                        "institution_type": guess_type(tags),
                        "street": tags.get("addr:street", ""),
                        "house_number": tags.get("addr:housenumber", ""),
                        "postcode": tags.get("addr:postcode", "").replace(" ", ""),
                        "city": extract_city(tags),
                        "phone": (tags.get("phone") or tags.get("contact:phone") or "")[:20],
                        "email": (tags.get("email") or tags.get("contact:email") or "")[:254],
                        "website": (tags.get("website") or tags.get("contact:website") or "")[:200],
                        "location": Point(float(lng), float(lat), srid=4326),
                        "is_active": True,
                    },
                )
                if flag:
                    created += 1
                else:
                    updated += 1

            self.stdout.write(f"  → {created} created, {updated} updated, {skipped} skipped")
            total_created += created
            total_updated += updated
            total_skipped += skipped

            # Be polite to Overpass API
            time.sleep(5)

        self.stdout.write(self.style.SUCCESS(
            f"\nTotal: {total_created} created, {total_updated} updated, {total_skipped} skipped"
        ))
