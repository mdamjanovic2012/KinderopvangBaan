"""
Management command: import_diplomacheck_api
Downloadt alle diploma's van de kinderopvang-werkt.nl API en importeert ze.

Gebruik:
    python manage.py import_diplomacheck_api
    python manage.py import_diplomacheck_api --dry-run
    python manage.py import_diplomacheck_api --clear
"""

import re
import requests
from django.core.management.base import BaseCommand
from diplomacheck.models import Diploma

API_URL = "https://www.kinderopvang-werkt.nl/possible-diplomas?time=0"

DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.kinderopvang-werkt.nl/",
}

# Haal de level-suffix uit de titel: "Diploma naam (mbo-4)" → "mbo-4"
LEVEL_SUFFIX_RE = re.compile(r"\s*\([^)]+\)\s*$")


def parse_level(raw: str) -> str:
    """Vertaal de ruwe level-string naar onze model-waarden."""
    r = raw.lower().strip()
    if "mbo-3" in r or "mbo 3" in r or r == "mbo3":
        return "mbo3"
    if "mbo-4" in r or "mbo 4" in r or r == "mbo4":
        return "mbo4"
    if "mbo-2" in r or "mbo 2" in r or r == "mbo2":
        return "mbo2"
    if "master" in r or "universitair" in r or "wo" == r:
        return "wo"
    # associate degree, hbo-bachelor, hbo/universitair, post-hbo, hbo → hbo
    return "hbo"


def parse_status(val: str) -> str:
    """
    Kinderopvang-werkt.nl veldwaarden:
      0 = niet bevoegd
      1 = direct bevoegd
      2 = met aanvullend bewijs
    """
    if val == "1":
        return "direct"
    if val == "2":
        return "proof_required"
    return "not_qualified"


def parse_entry(item: dict) -> dict | None:
    title = item.get("title", "").strip()
    if not title:
        return None

    # Extraheer level uit de titel suffix
    m = re.search(r"\(([^)]+)\)\s*$", title)
    level_raw = m.group(1) if m else ""
    level = parse_level(level_raw)

    # Naam zonder level suffix
    name = LEVEL_SUFFIX_RE.sub("", title).strip()
    if not name:
        return None

    kdv_status = parse_status(item.get("field_dagopvang", "0"))
    bso_status = parse_status(item.get("field_buitenschoolse_opvang", "0"))

    return {
        "name": name,
        "level": level,
        "kdv_status": kdv_status,
        "bso_status": bso_status,
        "notes": f"API nid={item.get('nid', '')}",
    }


class Command(BaseCommand):
    help = "Importeert alle diploma's van de kinderopvang-werkt.nl diplomacheck API"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Niet opslaan, alleen tellen")
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Verwijder bestaande API-diploma's eerst (notes startswith 'API nid=')",
        )

    def handle(self, *args, **options):
        self.stdout.write(f"Ophalen: {API_URL}")
        resp = requests.get(API_URL, headers=DOWNLOAD_HEADERS, timeout=30)
        if resp.status_code != 200:
            self.stderr.write(f"Download mislukt: HTTP {resp.status_code}")
            return

        data = resp.json()
        if not data.get("success"):
            self.stderr.write("API gaf geen success=true")
            return

        raw_list = data["diplomas"]
        self.stdout.write(f"Ontvangen: {len(raw_list)} items")

        entries = [e for item in raw_list if (e := parse_entry(item)) is not None]
        self.stdout.write(f"Geparseerd: {len(entries)} diploma-entries")

        if options["dry_run"]:
            for e in entries[:20]:
                self.stdout.write(
                    f"  [{e['level']:5}] {e['name'][:60]:<60} "
                    f"KDV={e['kdv_status'][:6]}  BSO={e['bso_status'][:6]}"
                )
            self.stdout.write(f"  ... en nog {max(0, len(entries) - 20)} meer")
            return

        if options["clear"]:
            deleted = Diploma.objects.filter(notes__startswith="API nid=").delete()[0]
            self.stdout.write(f"Verwijderd: {deleted} oud geïmporteerde API-diploma's")

        created = updated = skipped = 0
        for item in entries:
            if not item["name"]:
                skipped += 1
                continue
            obj, is_new = Diploma.objects.update_or_create(
                name=item["name"],
                level=item["level"],
                defaults={
                    "kdv_status": item["kdv_status"],
                    "bso_status": item["bso_status"],
                    "notes": item["notes"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Klaar: {created} nieuw, {updated} bijgewerkt, {skipped} overgeslagen"
            )
        )
