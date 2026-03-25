"""
Management command: enrich_from_lrk

Downloads the public LRK CSV and enriches existing Institution records with:
  - kvk_nummer_houder, naam_houder, gemeente, lrk_url
  - phone, email, website (only if currently empty)
  - parent FK (moeder-dochter) based on kvk_nummer_houder

SAFE: only UPDATEs existing records, never deletes or drops data.
Runs at most once per 30 days (timestamp stored in LRK_TIMESTAMP_FILE).

Usage:
    python manage.py enrich_from_lrk              # skip if < 30 days
    python manage.py enrich_from_lrk --force      # run regardless
    python manage.py enrich_from_lrk --dry-run    # show changes, don't save
    python manage.py enrich_from_lrk --csv /path/to/local.csv
"""

import csv
import io
import os
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from institutions.models import Institution

# Timestamp file — persists across deploys on Azure (/home/ is persistent)
_DEFAULT_TIMESTAMP_FILE = Path(
    os.environ.get("LRK_TIMESTAMP_FILE", "/home/.lrk_last_run")
    if not settings.LOCAL
    else str(Path(settings.BASE_DIR) / ".lrk_last_run")
)
ENRICH_INTERVAL_DAYS = 30

LRK_CSV_URL = "https://www.landelijkregisterkinderopvang.nl/opendata/export_opendata_lrk.csv"

# LRK CSV column → Institution field (only if field is currently empty)
CONTACT_FIELD_MAP = {
    "contact_telefoon": "phone",
    "contact_emailadres": "email",
    "contact_website": "website",
}


def _normalise_lrk_number(value):
    """LRK numbers in CSV may have leading zeros or spaces."""
    return (value or "").strip().lstrip("0") or None


def _clean(value):
    return (value or "").strip()


class Command(BaseCommand):
    help = "Enrich Institution records from the public LRK open-data CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would change without saving."
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Run even if last enrichment was less than 30 days ago."
        )
        parser.add_argument(
            "--csv", dest="csv_path", default=None,
            help="Path to a local CSV file instead of downloading."
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]
        csv_path = options["csv_path"]

        if not force and not dry_run and self._should_skip():
            self.stdout.write(self.style.WARNING(
                f"Skipping: last enrichment was less than {ENRICH_INTERVAL_DAYS} days ago. "
                "Use --force to override."
            ))
            return

        self.stdout.write("Loading LRK CSV…")
        rows = self._load_csv(csv_path)
        self.stdout.write(f"  {len(rows)} rows loaded.")

        # Build lookup: lrk_number (normalised) → row
        lrk_lookup = {}
        for row in rows:
            lrk = _normalise_lrk_number(row.get("lrk_id") or row.get("locatie_id") or "")
            if lrk:
                lrk_lookup[lrk] = row

        institutions = Institution.objects.all()
        updated = 0
        not_found = 0

        updates = []
        for inst in institutions:
            norm = _normalise_lrk_number(inst.lrk_number)
            if not norm or norm not in lrk_lookup:
                not_found += 1
                continue

            row = lrk_lookup[norm]
            changed = False

            # Enrich LRK-specific fields (always overwrite)
            for csv_col, field in [
                ("naam_houder", "naam_houder"),
                ("kvk_nummer_houder", "kvk_nummer_houder"),
                ("verantwoordelijke_gemeente", "gemeente"),
                ("lrk_url", "lrk_url"),
            ]:
                val = _clean(row.get(csv_col, ""))
                if val and getattr(inst, field) != val:
                    setattr(inst, field, val)
                    changed = True

            # Contact fields — only fill if currently empty
            for csv_col, field in CONTACT_FIELD_MAP.items():
                val = _clean(row.get(csv_col, ""))
                if val and not getattr(inst, field):
                    setattr(inst, field, val)
                    changed = True

            if changed:
                updates.append(inst)
                updated += 1

        self.stdout.write(f"  {updated} institutions to update, {not_found} not found in LRK.")

        if not dry_run and updates:
            with transaction.atomic():
                Institution.objects.bulk_update(
                    updates,
                    ["naam_houder", "kvk_nummer_houder", "gemeente", "lrk_url",
                     "phone", "email", "website"],
                    batch_size=500,
                )
            self.stdout.write(self.style.SUCCESS(f"  Saved {updated} updates."))

        # Parent-child linking
        self.stdout.write("Linking parent organisations by kvk_nummer_houder…")
        parent_count = self._link_parents(dry_run)
        self.stdout.write(self.style.SUCCESS(
            f"  {'Would link' if dry_run else 'Linked'} {parent_count} institutions to a parent."
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes saved."))
        else:
            self._write_timestamp()
            self.stdout.write(self.style.SUCCESS("Done."))

    def _load_csv(self, csv_path):
        if csv_path:
            with open(csv_path, encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
        else:
            with urllib.request.urlopen(LRK_CSV_URL, timeout=30) as response:
                content = response.read().decode("utf-8-sig", errors="replace")

        # Detect delimiter (LRK uses semicolons)
        dialect = csv.Sniffer().sniff(content[:2048], delimiters=";,")
        reader = csv.DictReader(io.StringIO(content), dialect=dialect)
        return [
            {k.strip().lower(): v for k, v in row.items()}
            for row in reader
        ]

    def _should_skip(self):
        ts_file = _DEFAULT_TIMESTAMP_FILE
        if not ts_file.exists():
            return False
        try:
            last_run = datetime.fromisoformat(ts_file.read_text().strip())
            return datetime.now() - last_run < timedelta(days=ENRICH_INTERVAL_DAYS)
        except (ValueError, OSError):
            return False

    def _write_timestamp(self):
        ts_file = _DEFAULT_TIMESTAMP_FILE
        try:
            ts_file.parent.mkdir(parents=True, exist_ok=True)
            ts_file.write_text(datetime.now().isoformat())
        except OSError as e:
            self.stderr.write(f"Warning: could not write timestamp file: {e}")

    def _link_parents(self, dry_run):
        """
        Group institutions by kvk_nummer_houder.
        When a group has >1 location, pick the 'oldest' (lowest pk) as the parent
        or the one whose naam matches naam_houder most closely.
        """
        groups = defaultdict(list)
        for inst in Institution.objects.exclude(kvk_nummer_houder="").values(
            "id", "kvk_nummer_houder", "naam_houder", "name"
        ):
            groups[inst["kvk_nummer_houder"]].append(inst)

        to_update = []
        linked = 0

        for kvk, members in groups.items():
            if len(members) < 2:
                continue

            # Pick parent: member whose name best matches naam_houder, else lowest pk
            naam_houder = members[0]["naam_houder"].lower()
            parent = min(
                members,
                key=lambda m: (
                    0 if naam_houder in m["name"].lower() else 1,
                    m["id"],
                ),
            )

            for member in members:
                if member["id"] != parent["id"]:
                    to_update.append(Institution(id=member["id"], parent_id=parent["id"]))
                    linked += 1

        if not dry_run and to_update:
            with transaction.atomic():
                Institution.objects.bulk_update(to_update, ["parent"], batch_size=500)

        return linked
