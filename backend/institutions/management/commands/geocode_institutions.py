"""
Geocodes institutions that have an address but no location (PointField).
Uses PDOK Locatieserver — free Dutch government geocoding API.
No API key required.

Usage:
    python manage.py geocode_institutions
    python manage.py geocode_institutions --limit 100
"""
import time
import requests
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from institutions.models import Institution

PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"


def geocode_dutch_address(street, house_number, postcode, city):
    """
    Returns (lng, lat) tuple or None.
    PDOK Locatieserver is optimised for Dutch addresses.
    """
    query = f"{street} {house_number}, {postcode} {city}"
    try:
        resp = requests.get(
            PDOK_URL,
            params={"q": query, "rows": 1, "fl": "centroide_ll"},
            timeout=5,
        )
        resp.raise_for_status()
        docs = resp.json().get("response", {}).get("docs", [])
        if not docs:
            return None
        centroid = docs[0].get("centroide_ll", "")
        # Format: "POINT(4.89 52.37)"
        if centroid.startswith("POINT("):
            coords = centroid[6:-1].split()
            return float(coords[0]), float(coords[1])  # lng, lat
    except Exception:
        pass
    return None


class Command(BaseCommand):
    help = "Geocode institutions using PDOK Locatieserver (free, NL government API)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max number of institutions to geocode (0 = all)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-geocode even if location already set",
        )

    def handle(self, *args, **options):
        qs = Institution.objects.all()
        if not options["force"]:
            qs = qs.filter(location__isnull=True)
        if options["limit"]:
            qs = qs[: options["limit"]]

        total = qs.count()
        self.stdout.write(f"Geocoding {total} institutions...")

        ok = 0
        failed = 0
        for inst in qs:
            result = geocode_dutch_address(
                inst.street, inst.house_number, inst.postcode, inst.city
            )
            if result:
                lng, lat = result
                inst.location = Point(lng, lat, srid=4326)
                inst.save(update_fields=["location"])
                ok += 1
                self.stdout.write(f"  ✓ {inst.name} → {lat:.4f}, {lng:.4f}")
            else:
                failed += 1
                self.stdout.write(
                    self.style.WARNING(f"  ✗ {inst.name} ({inst.postcode} {inst.city})")
                )
            # Be polite to the API
            time.sleep(0.1)

        self.stdout.write(
            self.style.SUCCESS(f"\nDone: {ok} geocoded, {failed} failed")
        )
