from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Diploma",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("crebo", models.CharField(blank=True, help_text="CREBO nummer (MBO)", max_length=20)),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("mbo2", "MBO niveau 2"),
                            ("mbo3", "MBO niveau 3"),
                            ("mbo4", "MBO niveau 4"),
                            ("hbo", "HBO"),
                            ("wo", "WO / Master"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "qualifying_roles",
                    models.JSONField(
                        default=list,
                        help_text="Lijst van CAO-functiewaarden waarvoor dit diploma kwalificeert",
                    ),
                ),
                (
                    "qualifying_institution_types",
                    models.JSONField(
                        default=list,
                        help_text="Instellingstypen: kdv, bso, peuterspeelzaal, gastouder",
                    ),
                ),
                ("notes", models.TextField(blank=True, help_text="Extra voorwaarden of toelichting")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["level", "name"],
            },
        ),
    ]
