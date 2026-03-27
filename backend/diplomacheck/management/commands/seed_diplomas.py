from django.core.management.base import BaseCommand
from diplomacheck.models import Diploma
from diplomacheck.data import DIPLOMA_DATA


class Command(BaseCommand):
    help = "Vult de database met erkende kinderopvang diploma's (CAO Kinderopvang)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Verwijder alle bestaande diploma's voor het seeden",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            count = Diploma.objects.all().delete()[0]
            self.stdout.write(f"Verwijderd: {count} diploma's")

        created = 0
        updated = 0
        for item in DIPLOMA_DATA:
            obj, is_new = Diploma.objects.update_or_create(
                name=item["name"],
                level=item["level"],
                defaults={
                    "crebo": item.get("crebo", ""),
                    "kdv_status": item.get("kdv_status", "not_qualified"),
                    "bso_status": item.get("bso_status", "not_qualified"),
                    "qualifying_roles": item["qualifying_roles"],
                    "qualifying_institution_types": item["qualifying_institution_types"],
                    "notes": item.get("notes", ""),
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Klaar: {created} nieuw aangemaakt, {updated} bijgewerkt"
            )
        )
