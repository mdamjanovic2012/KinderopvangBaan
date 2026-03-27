"""
Management command: update_diplomas
Combineert beide diploma-imports in één commando:
  1. Kinderopvang-werkt.nl API  (≈1020 diploma's)
  2. Officieel CAO Kinderopvang PDF bijlage 13-1  (≈229 diploma's)

Skip-logica: niet draaien als laatste run minder dan 180 dagen geleden was.
Sentinel: /home/.diploma_last_run (Azure persistent storage) of lokaal .diploma_last_run.

Gebruik:
    python manage.py update_diplomas            # skip als < 180 dagen geleden
    python manage.py update_diplomas --force    # altijd draaien
    python manage.py update_diplomas --dry-run  # tellen, niet opslaan
    python manage.py update_diplomas --status   # toon wanneer laatste run was
"""

import os
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

# Max 1x per 6 maanden (180 dagen)
INTERVAL_DAYS = 180

# Sentinel-bestand: persistent op Azure (/home/), lokaal in backend/
_SENTINEL = Path(
    os.environ.get("DIPLOMA_TIMESTAMP_FILE", "/home/.diploma_last_run")
    if not getattr(settings, "LOCAL", False)
    else str(Path(settings.BASE_DIR) / ".diploma_last_run")
)

# CAO PDF URL — jaardeel verandert elk jaar (2025-04 → 2026-04 etc.)
CAO_PDF_URL = (
    "https://www.kinderopvang-werkt.nl/sites/fcb_kinderopvang/files/2025-04/"
    "Bijlage-13-1-Cao-Kinderopvang-Diplomalijst-2025-2026.pdf"
)


def _last_run_date() -> date | None:
    """Geeft de datum van de laatste run, of None als nooit gedraaid."""
    try:
        text = _SENTINEL.read_text().strip()
        return date.fromisoformat(text[:10])
    except Exception:
        return None


def _days_since_last_run() -> int | None:
    last = _last_run_date()
    if last is None:
        return None
    return (date.today() - last).days


def _write_sentinel():
    _SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    _SENTINEL.write_text(date.today().isoformat())


class Command(BaseCommand):
    help = "Diploma-update: API + CAO PDF (max 1x per 180 dagen)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Altijd draaien, ook als < 180 dagen geleden",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Niet opslaan, alleen tellen",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Toon wanneer laatste run was en exit",
        )
        parser.add_argument(
            "--cao-url",
            default=CAO_PDF_URL,
            help="URL van de CAO PDF (voor nieuwe jaargang)",
        )

    def handle(self, *args, **options):
        last = _last_run_date()
        days_ago = _days_since_last_run()

        # ── --status ──────────────────────────────────────────────────────────
        if options["status"]:
            if last is None:
                self.stdout.write("DIPLOMA_STATUS: nooit gedraaid")
            else:
                next_run = last + timedelta(days=INTERVAL_DAYS)
                self.stdout.write(
                    f"DIPLOMA_STATUS: laatste run {last} ({days_ago} dagen geleden) — "
                    f"volgende run na {next_run}"
                )
            return

        # ── skip-check ────────────────────────────────────────────────────────
        if not options["force"] and not options["dry_run"]:
            if days_ago is not None and days_ago < INTERVAL_DAYS:
                self.stdout.write(
                    self.style.WARNING(
                        f"DIPLOMA_SKIP: laatste run was {days_ago} dagen geleden "
                        f"(threshold {INTERVAL_DAYS} dagen). Gebruik --force om te overschrijven."
                    )
                )
                return

        from diplomacheck.models import Diploma

        self.stdout.write(self.style.MIGRATE_HEADING("=== Diploma-update gestart ==="))
        if last:
            self.stdout.write(f"Vorige run: {last} ({days_ago} dagen geleden)")
        else:
            self.stdout.write("Vorige run: nooit")

        count_before = Diploma.objects.count()
        self.stdout.write(f"Diploma's vóór import: {count_before}")

        if options["dry_run"]:
            # Dry-run hoeft geen transactie — niets wordt opgeslagen
            self.stdout.write("\n[1/2] Import via kinderopvang-werkt.nl API (dry-run)...")
            call_command("import_diplomacheck_api", dry_run=True, clear=False)
            self.stdout.write("\n[2/2] Import via CAO PDF (dry-run)...")
            call_command("import_cao_pdf", url=options["cao_url"], dry_run=True, clear=False)
            self.stdout.write("\n=== Dry-run klaar — niets opgeslagen ===")
            return

        # ── Import in één atomaire transactie ────────────────────────────────
        # Als het aantal diploma's daalt na de import → automatisch rollback.
        # Bestaande diploma's blijven altijd bewaard.
        count_after = count_before

        try:
            with transaction.atomic():
                self.stdout.write("\n[1/2] Import via kinderopvang-werkt.nl API...")
                call_command("import_diplomacheck_api", dry_run=False, clear=False)

                self.stdout.write("\n[2/2] Import via CAO PDF...")
                call_command("import_cao_pdf", url=options["cao_url"], dry_run=False, clear=False)

                count_after = Diploma.objects.count()
                added = count_after - count_before

                if count_after < count_before:
                    # Rollback — transactie wordt teruggedraaid
                    raise ValueError(
                        f"DIPLOMA_ROLLBACK: aantal gedaald van {count_before} naar {count_after}. "
                        "Alle wijzigingen teruggedraaid."
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nDiploma's na import: {count_after} (+{added} nieuw)"
                    )
                )

        except ValueError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            self.stderr.write(
                self.style.WARNING(
                    f"Database hersteld naar {count_before} diploma's. "
                    "Sentinel NIET bijgewerkt — volgende deploy probeert opnieuw."
                )
            )
            return

        # ── Sentinel pas schrijven ná succesvolle commit ──────────────────────
        _write_sentinel()
        self.stdout.write(
            self.style.SUCCESS(
                f"DIPLOMA_DONE: sentinel geschreven op {date.today()} → {_SENTINEL}"
            )
        )
