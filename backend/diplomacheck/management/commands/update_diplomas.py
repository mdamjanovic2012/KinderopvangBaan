"""
Management command: update_diplomas
Combineert beide diploma-imports in één commando:
  1. Kinderopvang-werkt.nl API  (≈1020 diploma's)
  2. Officieel CAO Kinderopvang PDF bijlage 13-1  (≈229 diploma's)

Loopt automatisch tijdens deploy via startup.sh.
Skip als de import al eerder dit kalenderjaar is gedraaid.
Het sentinel-bestand wordt opgeslagen op Azure /home/ (persistent storage).

Gebruik:
    python manage.py update_diplomas            # skip als al dit jaar gedraaid
    python manage.py update_diplomas --force    # altijd draaien
    python manage.py update_diplomas --dry-run  # tellen, niet opslaan
"""

import os
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

# Sentinel-bestand: persistent op Azure (/home/), lokaal in backend/
_SENTINEL = Path(
    os.environ.get("DIPLOMA_TIMESTAMP_FILE", "/home/.diploma_last_run")
    if not getattr(settings, "LOCAL", False)
    else str(Path(settings.BASE_DIR) / ".diploma_last_run")
)

# CAO PDF URL — jaar-deel verandert elk jaar (2025-04 → 2026-04 etc.)
CAO_PDF_URL = (
    "https://www.kinderopvang-werkt.nl/sites/fcb_kinderopvang/files/2025-04/"
    "Bijlage-13-1-Cao-Kinderopvang-Diplomalijst-2025-2026.pdf"
)


def _last_run_year() -> int | None:
    """Geeft het jaar terug van de laatste run, of None als nooit gedraaid."""
    try:
        text = _SENTINEL.read_text().strip()
        return date.fromisoformat(text[:10]).year
    except Exception:
        return None


def _write_sentinel():
    _SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    _SENTINEL.write_text(date.today().isoformat())


class Command(BaseCommand):
    help = "Jaarlijkse diploma-update: API + CAO PDF (skip als al dit jaar gedraaid)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Altijd draaien, ook als al dit jaar gedraaid",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Niet opslaan, alleen tellen",
        )
        parser.add_argument(
            "--cao-url",
            default=CAO_PDF_URL,
            help="URL van de CAO PDF (voor nieuwe jaargang)",
        )

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]
        cao_url = options["cao_url"]

        current_year = date.today().year
        last_year = _last_run_year()

        if not force and not dry_run and last_year == current_year:
            self.stdout.write(
                self.style.WARNING(
                    f"Overgeslagen: diploma-update al gedraaid in {current_year}. "
                    "Gebruik --force om opnieuw te draaien."
                )
            )
            return

        self.stdout.write(self.style.MIGRATE_HEADING("=== Diploma-update gestart ==="))

        # ── Stap 1: kinderopvang-werkt.nl API ────────────────────────────────
        self.stdout.write("\n[1/2] Import via kinderopvang-werkt.nl API...")
        try:
            call_command(
                "import_diplomacheck_api",
                **{"dry_run": dry_run, "clear": False},
            )
        except Exception as e:
            self.stderr.write(f"API import mislukt: {e}")

        # ── Stap 2: officieel CAO PDF bijlage 13-1 ───────────────────────────
        self.stdout.write("\n[2/2] Import via CAO PDF...")
        try:
            call_command(
                "import_cao_pdf",
                url=cao_url,
                **{"dry_run": dry_run, "clear": False},
            )
        except Exception as e:
            self.stderr.write(f"PDF import mislukt: {e}")

        if not dry_run:
            _write_sentinel()
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n=== Diploma-update klaar — sentinel opgeslagen in {_SENTINEL} ==="
                )
            )
        else:
            self.stdout.write("\n=== Dry-run klaar — niets opgeslagen ===")
