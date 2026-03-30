"""
Management command: backup_db

Maakt een gecomprimeerde JSON-dump van alle Django-modellen via dumpdata
en uploadt deze naar Azure Blob Storage (container: db-backups).
Geen systeemafhankelijkheden — werkt puur via Python/Django.

Interval: max 1x per 7 dagen (sentinel: /home/.backup_last_run)
Retentie: max 30 backups; oudere worden automatisch verwijderd.

Gebruik:
    python manage.py backup_db              # overslaan als < 7 dagen geleden
    python manage.py backup_db --force      # altijd uitvoeren
    python manage.py backup_db --dry-run    # tonen wat er zou gebeuren
"""

import gzip
import io
import os
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

_DEFAULT_TIMESTAMP_FILE = Path(
    os.environ.get("BACKUP_TIMESTAMP_FILE", "/home/.backup_last_run")
    if not getattr(settings, "LOCAL", False)
    else str(Path(settings.BASE_DIR) / ".backup_last_run")
)

BACKUP_INTERVAL_DAYS = 7
BACKUP_RETENTION_COUNT = 30
BLOB_CONTAINER = "db-backups"


class Command(BaseCommand):
    help = "Backup alle Django-data naar Azure Blob Storage via dumpdata (geen pg_dump vereist)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Tonen wat er zou gebeuren zonder te uploaden.")
        parser.add_argument("--force", action="store_true",
                            help="Uitvoeren ook als < 7 dagen geleden.")

    def handle(self, *args, **options):
        if not options["force"] and not options["dry_run"] and self._should_skip():
            self.stdout.write(self.style.WARNING(
                f"Overgeslagen: laatste backup was minder dan {BACKUP_INTERVAL_DAYS} "
                "dagen geleden. Gebruik --force om te overschrijven."
            ))
            return

        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
        if not connection_string and not options["dry_run"]:
            self.stderr.write(self.style.ERROR(
                "AZURE_STORAGE_CONNECTION_STRING niet ingesteld. Backup overgeslagen."
            ))
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"backup_{timestamp}.json.gz"

        self.stdout.write(f"Database backup starten → {blob_name}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                f"Dry run — zou {blob_name} uploaden naar container '{BLOB_CONTAINER}'."
            ))
            return

        # Dump alle data via Django dumpdata → in-memory buffer
        buf = io.StringIO()
        call_command(
            "dumpdata",
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            stdout=buf,
        )
        json_data = buf.getvalue().encode("utf-8")

        # Comprimeer met gzip
        compressed = io.BytesIO()
        with gzip.GzipFile(fileobj=compressed, mode="wb") as gz:
            gz.write(json_data)
        size_mb = compressed.tell() / (1024 * 1024)
        compressed.seek(0)

        self.stdout.write(f"  Dump aangemaakt: {size_mb:.1f} MB (gecomprimeerd)")

        # Upload naar Azure Blob Storage
        self._upload_blob(connection_string, blob_name, compressed)
        self.stdout.write(self.style.SUCCESS(f"  Geüpload: {blob_name}"))

        self._prune_old_backups(connection_string)
        self._write_timestamp()
        self.stdout.write(self.style.SUCCESS("Backup klaar."))

    def _upload_blob(self, connection_string, blob_name, data):
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(connection_string)
        container = client.get_container_client(BLOB_CONTAINER)
        container.upload_blob(name=blob_name, data=data, overwrite=True)

    def _prune_old_backups(self, connection_string):
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(connection_string)
        container = client.get_container_client(BLOB_CONTAINER)
        blobs = sorted(
            container.list_blobs(),
            key=lambda b: b.last_modified,
            reverse=True,
        )
        for blob in blobs[BACKUP_RETENTION_COUNT:]:
            container.delete_blob(blob.name)
            self.stdout.write(f"  Oude backup verwijderd: {blob.name}")

    def _should_skip(self):
        ts_file = _DEFAULT_TIMESTAMP_FILE
        if not ts_file.exists():
            return False
        try:
            last_run = datetime.fromisoformat(ts_file.read_text().strip())
            return datetime.now() - last_run < timedelta(days=BACKUP_INTERVAL_DAYS)
        except (ValueError, OSError):
            return False

    def _write_timestamp(self):
        ts_file = _DEFAULT_TIMESTAMP_FILE
        try:
            ts_file.parent.mkdir(parents=True, exist_ok=True)
            ts_file.write_text(datetime.now().isoformat())
        except OSError as e:
            self.stderr.write(f"Waarschuwing: kon timestamp niet schrijven: {e}")
