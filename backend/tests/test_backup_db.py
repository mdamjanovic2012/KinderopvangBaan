"""
Tests for backup_db management command.
"""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from institutions.management.commands.backup_db import Command as BackupCommand


def _make_cmd():
    cmd = BackupCommand()
    cmd.stdout = MagicMock()
    cmd.stderr = MagicMock()
    cmd.style = MagicMock()
    cmd.style.WARNING = lambda s: s
    cmd.style.SUCCESS = lambda s: s
    cmd.style.ERROR = lambda s: s
    return cmd


# ---------------------------------------------------------------------------
# Timestamp: skip / force logic
# ---------------------------------------------------------------------------

class TestTimestamp:
    def test_should_skip_when_recent(self, tmp_path):
        ts_file = tmp_path / ".backup_last_run"
        ts_file.write_text(datetime.now().isoformat())
        cmd = _make_cmd()
        with patch("institutions.management.commands.backup_db._DEFAULT_TIMESTAMP_FILE", ts_file):
            assert cmd._should_skip() is True

    def test_should_not_skip_when_old(self, tmp_path):
        ts_file = tmp_path / ".backup_last_run"
        ts_file.write_text((datetime.now() - timedelta(days=8)).isoformat())
        cmd = _make_cmd()
        with patch("institutions.management.commands.backup_db._DEFAULT_TIMESTAMP_FILE", ts_file):
            assert cmd._should_skip() is False

    def test_should_not_skip_when_no_file(self, tmp_path):
        ts_file = tmp_path / ".backup_last_run"
        cmd = _make_cmd()
        with patch("institutions.management.commands.backup_db._DEFAULT_TIMESTAMP_FILE", ts_file):
            assert cmd._should_skip() is False

    def test_should_not_skip_with_corrupt_file(self, tmp_path):
        ts_file = tmp_path / ".backup_last_run"
        ts_file.write_text("not-a-date")
        cmd = _make_cmd()
        with patch("institutions.management.commands.backup_db._DEFAULT_TIMESTAMP_FILE", ts_file):
            assert cmd._should_skip() is False

    def test_write_timestamp_creates_file(self, tmp_path):
        ts_file = tmp_path / ".backup_last_run"
        cmd = _make_cmd()
        with patch("institutions.management.commands.backup_db._DEFAULT_TIMESTAMP_FILE", ts_file):
            cmd._write_timestamp()
        assert ts_file.exists()
        dt = datetime.fromisoformat(ts_file.read_text().strip())
        assert datetime.now() - dt < timedelta(seconds=5)


# ---------------------------------------------------------------------------
# handle(): skip / dry-run / missing env
# ---------------------------------------------------------------------------

class TestHandleSkipAndDryRun:
    def _run(self, **kwargs):
        cmd = _make_cmd()
        with patch.object(cmd, "_should_skip", return_value=False), \
             patch.object(cmd, "_get_db_url", return_value="postgresql://u:p@h/db"), \
             patch.object(cmd, "_pg_dump"), \
             patch.object(cmd, "_upload_blob"), \
             patch.object(cmd, "_prune_old_backups"), \
             patch.object(cmd, "_write_timestamp"):
            cmd.handle(**{"dry_run": False, "force": False, **kwargs})
        return cmd

    def test_skips_when_recent_and_no_force(self, tmp_path):
        ts_file = tmp_path / ".backup_last_run"
        ts_file.write_text(datetime.now().isoformat())
        cmd = _make_cmd()
        with patch("institutions.management.commands.backup_db._DEFAULT_TIMESTAMP_FILE", ts_file):
            cmd.handle(dry_run=False, force=False)
        cmd.stdout.write.assert_called_once()
        assert "Skipping" in cmd.stdout.write.call_args[0][0]

    def test_dry_run_does_not_upload(self):
        cmd = _make_cmd()
        with patch.object(cmd, "_should_skip", return_value=False), \
             patch.object(cmd, "_get_db_url", return_value="postgresql://u:p@h/db"), \
             patch.object(cmd, "_upload_blob") as mock_upload:
            cmd.handle(dry_run=True, force=False)
        mock_upload.assert_not_called()

    def test_missing_connection_string_skips(self):
        cmd = _make_cmd()
        with patch.object(cmd, "_should_skip", return_value=False), \
             patch.object(cmd, "_get_db_url", return_value="postgresql://u:p@h/db"), \
             patch.dict(os.environ, {}, clear=False):
            # ensure env var not set
            os.environ.pop("AZURE_STORAGE_CONNECTION_STRING", None)
            cmd.handle(dry_run=False, force=False)
        cmd.stderr.write.assert_called_once()

    def test_force_overrides_skip(self):
        """force=True should proceed even if timestamp is recent."""
        cmd = _make_cmd()
        with patch.object(cmd, "_should_skip", return_value=True), \
             patch.object(cmd, "_get_db_url", return_value="postgresql://u:p@h/db"), \
             patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "fake"}, clear=False), \
             patch.object(cmd, "_pg_dump"), \
             patch.object(cmd, "_upload_blob") as mock_upload, \
             patch.object(cmd, "_prune_old_backups"), \
             patch.object(cmd, "_write_timestamp"), \
             tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
            # pre-create temp file so unlink doesn't fail
            with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                mock_tmp.return_value.__enter__ = lambda s: s
                mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
                mock_tmp.return_value.name = tmp.name
                cmd.handle(dry_run=False, force=True)
        mock_upload.assert_called_once()


# ---------------------------------------------------------------------------
# _get_db_url
# ---------------------------------------------------------------------------

class TestGetDbUrl:
    def test_postgres_url_constructed(self, settings):
        settings.DATABASES = {
            "default": {
                "ENGINE": "django.contrib.gis.db.backends.postgis",
                "HOST": "myhost",
                "PORT": "5432",
                "NAME": "mydb",
                "USER": "myuser",
                "PASSWORD": "secret",
            }
        }
        cmd = _make_cmd()
        url = cmd._get_db_url()
        assert url == "postgresql://myuser:secret@myhost:5432/mydb"

    def test_non_postgres_returns_none(self, settings):
        settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}
        }
        cmd = _make_cmd()
        assert cmd._get_db_url() is None


# ---------------------------------------------------------------------------
# _pg_dump
# ---------------------------------------------------------------------------

class TestPgDump:
    def test_pg_dump_called_correctly(self):
        cmd = _make_cmd()
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            cmd._pg_dump("postgresql://u:p@h/db", "/tmp/test.dump")
        args = mock_run.call_args[0][0]
        assert args[0] == "pg_dump"
        assert "--format=custom" in args
        assert "/tmp/test.dump" in args

    def test_pg_dump_raises_on_failure(self):
        cmd = _make_cmd()
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "connection refused"
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="pg_dump failed"):
                cmd._pg_dump("postgresql://u:p@h/db", "/tmp/test.dump")


# ---------------------------------------------------------------------------
# _upload_blob / _prune_old_backups
# ---------------------------------------------------------------------------

class TestBlobOperations:
    def _mock_blob_client(self):
        mock_container = MagicMock()
        mock_service = MagicMock()
        mock_service.get_container_client.return_value = mock_container
        return mock_service, mock_container

    def test_upload_calls_upload_blob(self, tmp_path):
        test_file = tmp_path / "backup.dump"
        test_file.write_bytes(b"fake dump data")

        cmd = _make_cmd()
        mock_service, mock_container = self._mock_blob_client()
        with patch(
            "azure.storage.blob.BlobServiceClient.from_connection_string",
            return_value=mock_service,
        ):
            cmd._upload_blob("fake_conn_str", "backup_20260101.dump", str(test_file))
        mock_container.upload_blob.assert_called_once()

    def test_prune_deletes_oldest_over_limit(self):
        cmd = _make_cmd()
        mock_service, mock_container = self._mock_blob_client()

        # Create 35 fake blobs (should delete 5); use sequential timestamps
        from datetime import timezone
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        blobs = []
        for i in range(35):
            b = MagicMock()
            b.name = f"backup_{i:03d}.dump"
            b.last_modified = base + timedelta(days=i)
            blobs.append(b)
        mock_container.list_blobs.return_value = blobs

        with patch(
            "azure.storage.blob.BlobServiceClient.from_connection_string",
            return_value=mock_service,
        ):
            cmd._prune_old_backups("fake_conn_str")

        assert mock_container.delete_blob.call_count == 5

    def test_prune_does_nothing_under_limit(self):
        cmd = _make_cmd()
        mock_service, mock_container = self._mock_blob_client()

        from datetime import timezone
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        blobs = []
        for i in range(10):
            b = MagicMock()
            b.name = f"backup_{i:03d}.dump"
            b.last_modified = base + timedelta(days=i)
            blobs.append(b)
        mock_container.list_blobs.return_value = blobs

        with patch(
            "azure.storage.blob.BlobServiceClient.from_connection_string",
            return_value=mock_service,
        ):
            cmd._prune_old_backups("fake_conn_str")

        mock_container.delete_blob.assert_not_called()
