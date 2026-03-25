from rest_framework import serializers
from .models import Job, JobApplication


class JobSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    institution_city = serializers.CharField(source="institution.city", read_only=True)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "title", "job_type", "contract_type", "description",
            "institution", "institution_name", "institution_city",
            "city", "location",
            "salary_min", "salary_max", "hours_per_week",
            "requires_vog", "requires_diploma",
            "requires_bevoegdheid", "min_experience",
            "is_premium", "created_at", "expires_at",
            "distance_km",
        ]

    def get_distance_km(self, obj):
        if hasattr(obj, "distance"):
            return round(obj.distance.km, 2)
        return None


class JobApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = JobApplication
        fields = ["id", "job", "job_title", "cover_letter", "status", "created_at"]
        read_only_fields = ["id", "job", "status", "created_at", "job_title"]
