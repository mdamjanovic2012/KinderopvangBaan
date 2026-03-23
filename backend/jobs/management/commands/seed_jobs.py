from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from institutions.models import Institution
from jobs.models import Job

User = get_user_model()

DEMO_JOBS = [
    {
        "title": "Pedagogisch medewerker BSO",
        "job_type": "bso",
        "contract_type": "parttime",
        "description": (
            "Wij zoeken een enthousiaste pedagogisch medewerker voor onze BSO locatie in Amsterdam. "
            "Je begeleidt kinderen van 4 tot 12 jaar na schooltijd met creatieve activiteiten, sport en spel. "
            "\n\nWat wij vragen:\n- MBO niveau 3/4 Sociaal Pedagogisch Werker\n- Ervaring met basisschoolkinderen\n"
            "- Teamspeler met eigen initiatief\n\nWat wij bieden:\n- Flexibele werktijden\n- Prettige werksfeer\n- CAO Kinderopvang"
        ),
        "salary_min": 13.50,
        "salary_max": 16.00,
        "hours_per_week": 20,
        "requires_vog": True,
        "requires_diploma": True,
        "city_hint": "Amsterdam",
    },
    {
        "title": "Groepsleider KDV",
        "job_type": "kdv",
        "contract_type": "fulltime",
        "description": (
            "Voor ons kinderdagverblijf zoeken wij een ervaren groepsleider voor de babygroep (0-2 jaar). "
            "Je werkt in een hecht team en draagt bij aan een veilige en stimulerende omgeving voor de allerkleinsten. "
            "\n\nVereisten:\n- Diploma Pedagogisch Werker 3 of hoger\n- Minimaal 2 jaar ervaring\n- Warme en geduldige persoonlijkheid"
        ),
        "salary_min": 15.00,
        "salary_max": 18.50,
        "hours_per_week": 36,
        "requires_vog": True,
        "requires_diploma": True,
        "city_hint": "Amsterdam",
    },
    {
        "title": "ZZP Pedagogisch medewerker",
        "job_type": "kdv",
        "contract_type": "zzp",
        "description": (
            "Wij zoeken ZZP'ers die flexibel inzetbaar zijn bij ons KDV in Rotterdam. "
            "Ideaal voor ervaren krachten die zelfstandig willen werken. "
            "\n\nInzetbaar op:\n- Maandag t/m vrijdag, ochtend- en middagdiensten\n- Kortdurende invalverzoeken\n- Vakantieperiodes"
        ),
        "salary_min": 18.00,
        "salary_max": 22.00,
        "hours_per_week": None,
        "requires_vog": True,
        "requires_diploma": False,
        "city_hint": "Rotterdam",
    },
    {
        "title": "Nanny voor gezin in Den Haag",
        "job_type": "nanny",
        "contract_type": "parttime",
        "description": (
            "Gezin met 2 kinderen (2 en 5 jaar) zoekt een betrouwbare nanny voor 3 dagen per week. "
            "Werkzaamheden: ophalen van school, maaltijd bereiden, activiteiten begeleiden. "
            "\n\nTijden: ma/di/do van 14:00-18:30\nStartdatum: zo snel mogelijk"
        ),
        "salary_min": 14.00,
        "salary_max": 16.00,
        "hours_per_week": 14,
        "requires_vog": True,
        "requires_diploma": False,
        "city_hint": "Den Haag",
    },
    {
        "title": "BSO medewerker — Tijdelijke vervanging",
        "job_type": "bso",
        "contract_type": "temp",
        "description": (
            "Wij zoeken tijdelijke versterking voor onze BSO in Utrecht tijdens zwangerschapsverlof van een collega. "
            "Periode: 3 maanden met kans op verlenging. "
            "\n\nIdeaal voor recent afgestudeerden of zij-instromers die werkervaring willen opdoen."
        ),
        "salary_min": 13.00,
        "salary_max": 15.00,
        "hours_per_week": 24,
        "requires_vog": True,
        "requires_diploma": False,
        "city_hint": "Utrecht",
    },
]


class Command(BaseCommand):
    help = "Seed demo job listings linked to existing institutions"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Delete all existing jobs first")

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = Job.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} jobs.")

        # Get or create a system user to post jobs
        poster, _ = User.objects.get_or_create(
            username="system",
            defaults={"email": "system@kinderopvangbaan.nl", "role": "institution"},
        )

        institutions = list(Institution.objects.filter(is_active=True))
        if not institutions:
            self.stderr.write("No institutions found. Run import_lrk --demo first.")
            return

        created = 0
        for i, job_data in enumerate(DEMO_JOBS):
            city_hint = job_data.pop("city_hint")

            # Match institution by city
            matching = [inst for inst in institutions if city_hint.lower() in inst.city.lower()]
            institution = matching[0] if matching else institutions[i % len(institutions)]

            job, was_created = Job.objects.get_or_create(
                title=job_data["title"],
                institution=institution,
                defaults={
                    **job_data,
                    "posted_by": poster,
                    "location": institution.location,
                    "city": institution.city,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"  ✓ {job.title} @ {institution.name} ({institution.city})")

        self.stdout.write(self.style.SUCCESS(f"\nCreated {created} demo jobs."))
