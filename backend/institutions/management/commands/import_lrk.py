"""
Import childcare institutions from LRK (Landelijk Register Kinderopvang).

The Dutch government publishes LRK data as open data.
Download CSV from: https://www.landelijkregisterkinderopvang.nl/
  → Zoeken → Export (CSV)

Or use the open data portal:
  https://data.overheid.nl/dataset/landelijk-register-kinderopvang-en-peuterspeelzalen

Usage:
    python manage.py import_lrk --file /path/to/lrk_export.csv
    python manage.py import_lrk --file /path/to/lrk_export.csv --geocode
    python manage.py import_lrk --demo   # insert 10 demo institutions for testing
"""
import csv
import logging
import time
import requests
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import Point
from institutions.models import Institution

logger = logging.getLogger(__name__)

PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"

# Mapping from LRK type codes to our model choices
LRK_TYPE_MAP = {
    "BSO": Institution.TYPE_BSO,
    "KDV": Institution.TYPE_KDV,
    "Kinderdagverblijf": Institution.TYPE_KDV,
    "Gastouderbureau": Institution.TYPE_GASTOUDER,
    "Gastouder": Institution.TYPE_GASTOUDER,
    "Peuterspeelzaal": Institution.TYPE_PEUTERSPEELZAAL,
    "Peuteropvang": Institution.TYPE_PEUTERSPEELZAAL,
}

# Demo data for testing without a real CSV
DEMO_INSTITUTIONS = [
    {"name": "KDV De Kleine Kikker", "type": "KDV", "street": "Lijnbaansgracht", "hn": "214", "postcode": "1017RK", "city": "Amsterdam", "lrk": "LRK001"},
    {"name": "BSO De Zonnebloem", "type": "BSO", "street": "Vondelstraat", "hn": "45", "postcode": "1054GH", "city": "Amsterdam", "lrk": "LRK002"},
    {"name": "Gastouderbureau Hart voor Kids", "type": "Gastouder", "street": "Coolsingel", "hn": "12", "postcode": "3012AA", "city": "Rotterdam", "lrk": "LRK003"},
    {"name": "KDV Knuffelbeer", "type": "KDV", "street": "Binnenwegplein", "hn": "7", "postcode": "3012KA", "city": "Rotterdam", "lrk": "LRK004"},
    {"name": "BSO Speelpaleis", "type": "BSO", "street": "Grote Marktstraat", "hn": "52", "postcode": "2511BJ", "city": "Den Haag", "lrk": "LRK005"},
    {"name": "Peuterspeelzaal Regenboog", "type": "Peuterspeelzaal", "street": "Spui", "hn": "10", "postcode": "2511BK", "city": "Den Haag", "lrk": "LRK006"},
    {"name": "KDV De Vliegerende Vos", "type": "KDV", "street": "Lange Viestraat", "hn": "8", "postcode": "3511BK", "city": "Utrecht", "lrk": "LRK007"},
    {"name": "BSO Zonneschijn", "type": "BSO", "street": "Vredenburg", "hn": "20", "postcode": "3511BA", "city": "Utrecht", "lrk": "LRK008"},
    {"name": "KDV Fijnbos", "type": "KDV", "street": "Grote Markt", "hn": "1", "postcode": "9711LP", "city": "Groningen", "lrk": "LRK009"},
    {"name": "BSO De Sterrenvangers", "type": "BSO", "street": "Vismarkt", "hn": "5", "postcode": "9711KX", "city": "Groningen", "lrk": "LRK010"},
]


def geocode(street, hn, postcode, city):
    query = f"{street} {hn}, {postcode} {city}"
    try:
        resp = requests.get(
            PDOK_URL,
            params={"q": query, "rows": 1, "fl": "centroide_ll"},
            timeout=5,
        )
        docs = resp.json().get("response", {}).get("docs", [])
        if docs:
            centroid = docs[0].get("centroide_ll", "")
            if centroid.startswith("POINT("):
                lng, lat = centroid[6:-1].split()
                return Point(float(lng), float(lat), srid=4326)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Geocoding failed for query %r: %s", query, exc)
    return None


class Command(BaseCommand):
    help = "Import LRK institutions from CSV export or demo data"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, help="Path to LRK CSV export file")
        parser.add_argument("--geocode", action="store_true", help="Geocode addresses via PDOK")
        parser.add_argument("--demo", action="store_true", help="Insert 10 demo institutions")
        parser.add_argument("--clear", action="store_true", help="Clear all institutions before import")

    def handle(self, *args, **options):
        if options["clear"]:
            count = Institution.objects.count()
            Institution.objects.all().delete()
            self.stdout.write(f"Cleared {count} existing institutions.")

        if options["demo"]:
            self._import_demo(options["geocode"])
        elif options["file"]:
            self._import_csv(options["file"], options["geocode"])
        else:
            raise CommandError("Provide --file <path> or --demo")

    def _import_demo(self, do_geocode):
        self.stdout.write("Importing 10 demo institutions...")
        created = 0
        for d in DEMO_INSTITUTIONS:
            inst_type = LRK_TYPE_MAP.get(d["type"], Institution.TYPE_KDV)
            location = None
            if do_geocode:
                location = geocode(d["street"], d["hn"], d["postcode"], d["city"])
                time.sleep(0.15)

            # Fallback: rough coords per city if no geocode
            if not location:
                city_coords = {
                    "Amsterdam": (4.9041, 52.3676),
                    "Rotterdam": (4.4777, 51.9244),
                    "Den Haag": (4.3007, 52.0705),
                    "Utrecht": (5.1214, 52.0907),
                    "Groningen": (6.5665, 53.2194),
                }
                if d["city"] in city_coords:
                    lng, lat = city_coords[d["city"]]
                    location = Point(lng, lat, srid=4326)

            inst, created_flag = Institution.objects.update_or_create(
                lrk_number=d["lrk"],
                defaults={
                    "name": d["name"],
                    "institution_type": inst_type,
                    "street": d["street"],
                    "house_number": d["hn"],
                    "postcode": d["postcode"],
                    "city": d["city"],
                    "location": location or Point(5.2913, 52.1326, srid=4326),  # NL center fallback
                    "is_active": True,
                },
            )
            status = "created" if created_flag else "updated"
            self.stdout.write(f"  {status}: {inst.name} ({inst.city})")
            if created_flag:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone: {created} institutions imported."))

    def _import_csv(self, filepath, do_geocode):
        """
        Expected CSV columns (LRK export format):
        Naam, Soort, Straat, Huisnummer, Postcode, Plaatsnaam, LRK_nummer
        Column names may vary — adjust the mapping below.
        """
        COLUMN_MAP = {
            "name":      ["Naam", "naam", "Name"],
            "type":      ["Soort", "soort", "Type", "Voorziening"],
            "street":    ["Straat", "straat", "Street"],
            "hn":        ["Huisnummer", "huisnummer", "HuisNr"],
            "postcode":  ["Postcode", "postcode"],
            "city":      ["Plaatsnaam", "plaatsnaam", "Stad", "Gemeente"],
            "lrk":       ["LRK_nummer", "LRKnummer", "Registratienummer"],
        }

        def get_col(row, key):
            for col in COLUMN_MAP[key]:
                if col in row:
                    return row[col].strip()
            return ""

        try:
            with open(filepath, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                created = updated = skipped = 0

                for row in reader:
                    name = get_col(row, "name")
                    if not name:
                        skipped += 1
                        continue

                    raw_type = get_col(row, "type")
                    inst_type = LRK_TYPE_MAP.get(raw_type, Institution.TYPE_KDV)
                    street = get_col(row, "street")
                    hn = get_col(row, "hn")
                    postcode = get_col(row, "postcode").replace(" ", "")
                    city = get_col(row, "city")
                    lrk = get_col(row, "lrk") or None

                    location = None
                    if do_geocode and street and postcode:
                        location = geocode(street, hn, postcode, city)
                        time.sleep(0.1)

                    defaults = {
                        "name": name,
                        "institution_type": inst_type,
                        "street": street,
                        "house_number": hn,
                        "postcode": postcode,
                        "city": city,
                        "is_active": True,
                    }
                    if location:
                        defaults["location"] = location

                    if lrk:
                        inst, flag = Institution.objects.update_or_create(
                            lrk_number=lrk, defaults=defaults
                        )
                    else:
                        inst, flag = Institution.objects.update_or_create(
                            name=name, postcode=postcode, defaults=defaults
                        )

                    if flag:
                        created += 1
                    else:
                        updated += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Done: {created} created, {updated} updated, {skipped} skipped"
                    )
                )
        except FileNotFoundError:
            raise CommandError(f"File not found: {filepath}")
