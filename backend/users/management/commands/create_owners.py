"""
Management command: create_owners

Maakt de twee eigenaar-superuser accounts aan (Milos en Miki).
Wachtwoorden worden gelezen uit omgevingsvariabelen — nooit in de code.

Gebruik:
    OWNER_MILOS_PASSWORD=xxx OWNER_MIKI_PASSWORD=yyy python manage.py create_owners
    python manage.py create_owners --update     # update bestaande accounts
    python manage.py create_owners --dry-run    # toon wat er zou gebeuren

Omgevingsvariabelen:
    OWNER_MILOS_PASSWORD   Wachtwoord voor Milos (verplicht tenzij --dry-run)
    OWNER_MIKI_PASSWORD    Wachtwoord voor Miki  (verplicht tenzij --dry-run)
"""

import os

from django.core.management.base import BaseCommand, CommandError

from users.models import User

OWNERS = [
    {
        "username": "milos",
        "email": "milos@kinderopvangbaan.nl",
        "first_name": "Milos",
        "last_name": "Damjanovic",
        "env_password": "OWNER_MILOS_PASSWORD",
    },
    {
        "username": "miki",
        "email": "miki@kinderopvangbaan.nl",
        "first_name": "Miki",
        "last_name": "",
        "env_password": "OWNER_MIKI_PASSWORD",
    },
]


class Command(BaseCommand):
    help = "Maak eigenaar-superuser accounts aan voor Milos en Miki."

    def add_arguments(self, parser):
        parser.add_argument(
            "--update", action="store_true",
            help="Update bestaande accounts (wachtwoord, e-mail, is_staff).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Toon wat er zou gebeuren zonder wijzigingen op te slaan.",
        )

    def handle(self, *args, **options):
        update = options["update"]
        dry_run = options["dry_run"]

        for owner in OWNERS:
            username = owner["username"]
            password = os.environ.get(owner["env_password"], "")

            if not dry_run and not password:
                raise CommandError(
                    f"Omgevingsvariabele {owner['env_password']} is niet ingesteld. "
                    f"Gebruik: {owner['env_password']}=geheimwachtwoord python manage.py create_owners"
                )

            exists = User.objects.filter(username=username).exists()

            if dry_run:
                status = "bestaat al" if exists else "wordt aangemaakt"
                self.stdout.write(f"  [dry-run] {username} ({owner['email']}) — {status}")
                continue

            if exists and not update:
                self.stdout.write(self.style.WARNING(
                    f"  {username} bestaat al. Gebruik --update om bij te werken."
                ))
                continue

            if exists:
                user = User.objects.get(username=username)
                user.email = owner["email"]
                user.first_name = owner["first_name"]
                user.last_name = owner["last_name"]
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"  Bijgewerkt: {username}"))
            else:
                User.objects.create_superuser(
                    username=username,
                    email=owner["email"],
                    password=password,
                    first_name=owner["first_name"],
                    last_name=owner["last_name"],
                )
                self.stdout.write(self.style.SUCCESS(f"  Aangemaakt: {username}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — geen wijzigingen opgeslagen."))
        else:
            self.stdout.write(self.style.SUCCESS("Klaar."))
