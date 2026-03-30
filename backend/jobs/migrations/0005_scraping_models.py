"""
Migratie: scraping architectuur

- Verwijdert JobApplication model
- Verwijdert Job.posted_by en Job.institution (niet meer nodig voor scraping)
- Verwijdert Job.hours_per_week (vervangen door hours_min + hours_max)
- Voegt Company, GeocodedLocation, VacatureClick toe
- Voegt scraping-velden toe aan Job
- Wist alle bestaande Job records (incompatibel schema, geen productiedata)
"""

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def clear_jobs(apps, schema_editor):
    """Wis alle bestaande Job records — schema is incompatibel met scraping model."""
    Job = apps.get_model("jobs", "Job")
    Job.objects.all().delete()


class Migration(migrations.Migration):

    atomic = False  # PostgreSQL: pending trigger events bij FK-wijzigingen in één transactie

    dependencies = [
        ("jobs", "0004_add_requires_bevoegdheid_min_experience"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Verwijder JobApplication (FK naar Job) eerst ──────────────────────
        migrations.DeleteModel(name="JobApplication"),

        # ── Verwijder FK-velden van Job ───────────────────────────────────────
        migrations.RemoveField(model_name="job", name="posted_by"),
        migrations.RemoveField(model_name="job", name="institution"),

        # ── Wis incompatibele Job-data (na FK-verwijdering) ───────────────────
        migrations.RunPython(clear_jobs, migrations.RunPython.noop),
        migrations.RemoveField(model_name="job", name="hours_per_week"),
        migrations.RemoveField(model_name="job", name="expires_at"),

        # ── Maak Company aan ──────────────────────────────────────────────────
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("website", models.URLField(blank=True)),
                ("job_board_url", models.URLField()),
                ("scraper_class", models.CharField(help_text="bijv. KinderdamScraper", max_length=100)),
                ("logo_url", models.URLField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("last_scraped_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"], "verbose_name_plural": "companies"},
        ),

        # ── Maak GeocodedLocation aan ─────────────────────────────────────────
        migrations.CreateModel(
            name="GeocodedLocation",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("location_name", models.CharField(max_length=255, unique=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("postcode", models.CharField(blank=True, max_length=10)),
                ("municipality", models.CharField(blank=True, max_length=100)),
                ("location", django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
                ("geocoded_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["location_name"]},
        ),

        # ── Voeg company FK toe aan Job ───────────────────────────────────────
        migrations.AddField(
            model_name="job",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="jobs",
                to="jobs.company",
                null=True,  # tijdelijk nullable voor de migratie
            ),
        ),

        # ── Voeg nieuwe Job-velden toe ────────────────────────────────────────
        migrations.AddField(
            model_name="job",
            name="short_description",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="location_name",
            field=models.CharField(blank=True, max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="postcode",
            field=models.CharField(blank=True, max_length=10, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="hours_min",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="hours_max",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="age_min",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="age_max",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="source_url",
            field=models.URLField(default="", unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="external_id",
            field=models.CharField(blank=True, max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="last_seen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="is_expired",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="job",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),

        # ── Maak job_type en contract_type blank-able ─────────────────────────
        migrations.AlterField(
            model_name="job",
            name="job_type",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name="job",
            name="contract_type",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name="job",
            name="description",
            field=models.TextField(blank=True),
        ),

        # ── Maak company FK non-nullable ──────────────────────────────────────
        migrations.AlterField(
            model_name="job",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="jobs",
                to="jobs.company",
            ),
        ),

        # ── Maak VacatureClick aan ────────────────────────────────────────────
        migrations.CreateModel(
            name="VacatureClick",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("clicked_at", models.DateTimeField(auto_now_add=True)),
                ("ip_hash", models.CharField(blank=True, max_length=64)),
                ("job", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="clicks",
                    to="jobs.job",
                )),
                ("user", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="vacature_clicks",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-clicked_at"]},
        ),
    ]
