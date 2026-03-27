from rest_framework import serializers
from .models import Diploma

ROLE_LABELS = {
    "assistent_pm": "Assistent pedagogisch medewerker",
    "pm3": "Pedagogisch medewerker (niveau 3)",
    "pm4": "Pedagogisch medewerker (niveau 4)",
    "senior_pm": "Senior pedagogisch medewerker",
    "bso_begeleider": "Groepsbegeleider BSO",
    "coordinator_bso": "Coördinator BSO",
    "teamleider": "Teamleider kinderopvang",
    "locatiemanager": "Locatiemanager / Vestigingsmanager",
    "beleidsmedewerker": "Pedagogisch beleidsmedewerker",
    "gastouder": "Gastouder",
    "nanny": "Nanny",
    "stagiair": "Stagiair (BBL/BOL)",
}

INSTITUTION_TYPE_LABELS = {
    "kdv": "KDV / Kinderdagverblijf",
    "bso": "BSO",
    "peuterspeelzaal": "Peuterspeelzaal",
    "gastouder": "Gastouderbureau",
}


class DiplomaSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source="get_level_display", read_only=True)
    kdv_status_display = serializers.CharField(source="get_kdv_status_display", read_only=True)
    bso_status_display = serializers.CharField(source="get_bso_status_display", read_only=True)
    qualifying_roles_display = serializers.SerializerMethodField()
    qualifying_institution_types_display = serializers.SerializerMethodField()

    class Meta:
        model = Diploma
        fields = [
            "id",
            "name",
            "crebo",
            "level",
            "level_display",
            "kdv_status",
            "kdv_status_display",
            "bso_status",
            "bso_status_display",
            "qualifying_roles",
            "qualifying_roles_display",
            "qualifying_institution_types",
            "qualifying_institution_types_display",
            "notes",
        ]

    def get_qualifying_roles_display(self, obj):
        return [
            {"value": r, "label": ROLE_LABELS.get(r, r)}
            for r in obj.qualifying_roles
        ]

    def get_qualifying_institution_types_display(self, obj):
        return [
            {"value": t, "label": INSTITUTION_TYPE_LABELS.get(t, t)}
            for t in obj.qualifying_institution_types
        ]


class DiplomaSearchSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Diploma
        fields = ["id", "name", "crebo", "level", "level_display", "kdv_status", "bso_status"]
