from django.db import models


class Diploma(models.Model):
    QUAL_DIRECT = "direct"
    QUAL_PROOF = "proof_required"
    QUAL_NONE = "not_qualified"
    QUAL_CHOICES = [
        (QUAL_DIRECT, "Direct bevoegd"),
        (QUAL_PROOF, "Bevoegd met aanvullend bewijs"),
        (QUAL_NONE, "Niet bevoegd"),
    ]

    LEVEL_MBO2 = "mbo2"
    LEVEL_MBO3 = "mbo3"
    LEVEL_MBO4 = "mbo4"
    LEVEL_HBO = "hbo"
    LEVEL_WO = "wo"
    LEVEL_CHOICES = [
        (LEVEL_MBO2, "MBO niveau 2"),
        (LEVEL_MBO3, "MBO niveau 3"),
        (LEVEL_MBO4, "MBO niveau 4"),
        (LEVEL_HBO, "HBO"),
        (LEVEL_WO, "WO / Master"),
    ]

    name = models.CharField(max_length=255)
    crebo = models.CharField(max_length=20, blank=True, help_text="CREBO nummer (MBO)")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)

    # Welke CAO-functies zijn toegestaan met dit diploma?
    # Waarden uit jobs.constants.CAO_FUNCTION_VALUES
    qualifying_roles = models.JSONField(
        default=list,
        help_text="Lijst van CAO-functiewaarden waarvoor dit diploma kwalificeert",
    )

    # Voor welke instellingstypen (kdv, bso, peuterspeelzaal, gastouder)?
    qualifying_institution_types = models.JSONField(
        default=list,
        help_text="Instellingstypen: kdv, bso, peuterspeelzaal, gastouder",
    )

    # Per instellingstype kwalificatiestatus (voor de diplomacheck UI)
    kdv_status = models.CharField(
        max_length=20,
        choices=QUAL_CHOICES,
        default=QUAL_NONE,
        help_text="Kwalificatiestatus voor KDV / Dagopvang",
    )
    bso_status = models.CharField(
        max_length=20,
        choices=QUAL_CHOICES,
        default=QUAL_NONE,
        help_text="Kwalificatiestatus voor BSO",
    )

    notes = models.TextField(
        blank=True,
        help_text="Extra voorwaarden of toelichting",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["level", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"
