from rest_framework import serializers
from .models import Company, Job, VacatureClick


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "slug", "website", "logo_url"]


class JobSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_logo = serializers.CharField(source="company.logo_url", read_only=True)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "title", "job_type", "contract_type",
            "short_description", "description",
            "company", "company_name", "company_logo",
            "location_name", "city", "postcode", "location",
            "salary_min", "salary_max",
            "hours_min", "hours_max",
            "age_min", "age_max",
            "requires_vog", "requires_diploma",
            "requires_bevoegdheid", "min_experience",
            "is_premium", "is_expired",
            "source_url", "created_at", "expires_at",
            "distance_km",
        ]

    def get_distance_km(self, obj):
        if hasattr(obj, "distance"):
            return round(obj.distance.km, 2)
        return None


class VacatureClickSerializer(serializers.ModelSerializer):
    source_url = serializers.CharField(source="job.source_url", read_only=True)

    class Meta:
        model = VacatureClick
        fields = ["id", "job", "clicked_at", "source_url"]
        read_only_fields = ["id", "clicked_at", "source_url"]
