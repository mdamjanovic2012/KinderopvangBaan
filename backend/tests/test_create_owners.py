"""
Tests voor create_owners management command.
"""
import pytest
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError

from users.models import User


def _run(**kwargs):
    env = {
        "OWNER_MILOS_PASSWORD": "MilosSecret123",
        "OWNER_MIKI_PASSWORD": "MikiSecret456",
    }
    with patch.dict("os.environ", env, clear=False):
        call_command("create_owners", **kwargs)


@pytest.mark.django_db
class TestCreateOwners:
    def test_creates_milos_and_miki(self):
        _run()
        assert User.objects.filter(username="milos", is_superuser=True).exists()
        assert User.objects.filter(username="miki", is_superuser=True).exists()

    def test_users_are_staff_and_active(self):
        _run()
        for username in ["milos", "miki"]:
            user = User.objects.get(username=username)
            assert user.is_staff is True
            assert user.is_active is True

    def test_milos_has_correct_name(self):
        _run()
        user = User.objects.get(username="milos")
        assert user.first_name == "Milos"
        assert user.email == "milos@kinderopvangbaan.nl"

    def test_miki_has_correct_email(self):
        _run()
        user = User.objects.get(username="miki")
        assert user.email == "miki@kinderopvangbaan.nl"

    def test_does_not_overwrite_without_update_flag(self):
        _run()
        User.objects.filter(username="milos").update(email="changed@test.com")
        _run()  # zonder --update
        user = User.objects.get(username="milos")
        assert user.email == "changed@test.com"  # niet overschreven

    def test_update_flag_overwrites_email(self):
        _run()
        User.objects.filter(username="milos").update(email="old@test.com")
        _run(update=True)
        user = User.objects.get(username="milos")
        assert user.email == "milos@kinderopvangbaan.nl"

    def test_update_flag_changes_password(self):
        _run()
        env_new = {
            "OWNER_MILOS_PASSWORD": "NieuwWachtwoord999",
            "OWNER_MIKI_PASSWORD": "MikiSecret456",
        }
        with patch.dict("os.environ", env_new, clear=False):
            call_command("create_owners", update=True)
        user = User.objects.get(username="milos")
        assert user.check_password("NieuwWachtwoord999")

    def test_dry_run_makes_no_changes(self):
        call_command("create_owners", dry_run=True)
        assert not User.objects.filter(username="milos").exists()
        assert not User.objects.filter(username="miki").exists()

    def test_missing_password_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            # Verwijder wachtwoord env vars
            import os
            os.environ.pop("OWNER_MILOS_PASSWORD", None)
            os.environ.pop("OWNER_MIKI_PASSWORD", None)
            with pytest.raises((CommandError, SystemExit)):
                call_command("create_owners")

    def test_passwords_are_hashed(self):
        _run()
        user = User.objects.get(username="milos")
        assert not user.password.startswith("MilosSecret")
        assert user.check_password("MilosSecret123")
