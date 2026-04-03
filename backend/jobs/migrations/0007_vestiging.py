import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0006_company_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="Branch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("company_slug", models.SlugField(max_length=100)),
                ("name", models.CharField(max_length=255)),
                ("street", models.CharField(blank=True, max_length=255)),
                ("postcode", models.CharField(blank=True, max_length=10)),
                ("city", models.CharField(blank=True, max_length=100)),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True, null=True, srid=4326
                    ),
                ),
                ("geocoded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "branch",
                "verbose_name_plural": "branches",
                "ordering": ["company_slug", "name"],
                "db_table": "jobs_vestiging",
            },
        ),
        migrations.AlterUniqueTogether(
            name="branch",
            unique_together={("company_slug", "name")},
        ),
    ]
