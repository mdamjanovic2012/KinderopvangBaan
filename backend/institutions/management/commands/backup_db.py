"""
Management command: backup_db

Creates a pg_dump of the PostgreSQL database and uploads it to Azure Blob Storage.
Runs at most once per 7 days (timestamp stored in BACKUP_TIMESTAMP_FILE).
Keeps up to 30 backups; older ones are deleted automatically.

SAFE: read-only operation on the database, no data is modified.

Usage:
    python manage.py backup_db              # skip if < 7 days
    python manage.py backup_db --force      # run regardless
    python manage.py backup_db --dry-run    # show what would happen, don't upload
"""

import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Timestamp file — persists across deploys on Azure (/home/ is persistent)
_DEFAULT_TIMESTAMP_FILE = Path(
    os.environ.get("BACKUP_TIMESTAMP_FILE", "/home/.backup_last_run")
    if not settings.LOCAL
    else str(Path(settings.BASE_DIR) / ".backup_last_run")
)

BACKUP_INTERVAL_DAYS = 7
BACKUP_RETENTION_COUNT = 30
BLOB_CONTAINER = "db-backups"


class Command(BaseCommand):
    help = "Backup PostgreSQL database to Azure Blob Storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would happen without uploading.",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Run even if last backup was less than 7 days ago.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        if not force and not dry_run and self._should_skip():
            self.stdout.write(self.style.WARNING(
                f"Skipping: last backup was less than {BACKUP_INTERVAL_DAYS} days ago. "
                "Use --force to override."
            ))
            return

        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
        if not connection_string and not dry_run:
            self.stderr.write(self.style.ERROR(
                "AZURE_STORAGE_CONNECTION_STRING not set. Skipping backup."
            ))
            return

        db_url = self._get_db_url()
        if not db_url:
            self.stderr.write(self.style.ERROR("Could not determine database URL."))
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"backup_{timestamp}.dump"

        self.stdout.write(f"Starting database backup → {blob_name}")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"Dry run — would upload {blob_name} to container '{BLOB_CONTAINER}'."
            ))
            return

        with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self._pg_dump(db_url, tmp_path)
            size_mb = Path(tmp_path).stat().st_size / (1024 * 1024)
            self.stdout.write(f"  Dump created: {size_mb:.1f} MB")

            self._upload_blob(connection_string, blob_name, tmp_path)
            self.stdout.write(self.style.SUCCESS(f"  Uploaded {blob_name}"))

            self._prune_old_backups(connection_string)
            self._write_timestamp()
            self.stdout.write(self.style.SUCCESS("Backup complete."))

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _get_db_url(self):
        db = settings.DATABASES.get("default", {})
        engine = db.get("ENGINE", "")
        if "postgresql" not in engine and "postgis" not in engine:
            return None
        host = db.get("HOST", "localhost")
        port = db.get("PORT", "5432")
        name = db.get("NAME", "")
        user = db.get("USER", "")
        password = db.get("PASSWORD", "")
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    def _pg_dump(self, db_url, output_path):
        result = subprocess.run(
            ["pg_dump", "--format=custom", "--no-password", db_url,
             "--file", output_path],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

    def _upload_blob(self, connection_string, blob_name, file_path):
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(connection_string)
        container = client.get_container_client(BLOB_CONTAINER)
        with open(file_path, "rb") as data:
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
        to_delete = blobs[BACKUP_RETENTION_COUNT:]
        for blob in to_delete:
            container.delete_blob(blob.name)
            self.stdout.write(f"  Pruned old backup: {blob.name}")

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
            self.stderr.write(f"Warning: could not write timestamp file: {e}")
