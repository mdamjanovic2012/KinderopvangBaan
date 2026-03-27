"""
Management command: create_admin_users

Maakt twee admin-gebruikers aan:
  - Milos: superuser (volledig toegang)
  - Miki:  read-only staff (alleen bekijken in admin)

Gebruik:
    python manage.py create_admin_users
    python manage.py create_admin_users --milos-password geheimww --miki-password geheimww2
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

User = get_user_model()

DEFAULT_MILOS_PW = "Admin@Baan2026!"
DEFAULT_MIKI_PW  = "ReadOnly@Baan2026!"


class Command(BaseCommand):
    help = "Maak admin-gebruikers aan: Milos (superuser) en Miki (read-only)"

    def add_arguments(self, parser):
        parser.add_argument("--milos-password", default=DEFAULT_MILOS_PW)
        parser.add_argument("--miki-password",  default=DEFAULT_MIKI_PW)

    def handle(self, *args, **options):
        self._create_milos(options["milos_password"])
        self._create_miki(options["miki_password"])

    def _create_milos(self, password):
        user, created = User.objects.get_or_create(username="Milos")
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        status = "aangemaakt" if created else "bijgewerkt"
        self.stdout.write(self.style.SUCCESS(f"Milos ({status}) — superuser"))

    def _create_miki(self, password):
        user, created = User.objects.get_or_create(username="Miki")
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = False
        user.save()

        # Geef alle view-permissies maar geen add/change/delete
        view_perms = Permission.objects.filter(codename__startswith="view_")
        user.user_permissions.set(view_perms)

        status = "aangemaakt" if created else "bijgewerkt"
        self.stdout.write(self.style.SUCCESS(
            f"Miki ({status}) — read-only staff ({view_perms.count()} view-permissies)"
        ))
