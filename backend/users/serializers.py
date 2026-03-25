from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import WorkerProfile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role", "first_name", "last_name"]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def validate_role(self, value):
        allowed = {User.ROLE_WORKER, User.ROLE_INSTITUTION}
        if value not in allowed:
            raise serializers.ValidationError(
                "Registratie is alleen mogelijk als professional of organisatie."
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "phone", "avatar", "first_name", "last_name"]
        read_only_fields = ["id"]


class WorkerProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    has_vog = serializers.BooleanField()
    has_diploma = serializers.BooleanField()

    class Meta:
        model = WorkerProfile
        exclude = ["user", "vog_verified", "diploma_verified", "is_premium"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PublicWorkerSerializer(serializers.ModelSerializer):
    """Public-facing worker profile — limited fields."""
    username = serializers.CharField(source="user.username", read_only=True)
    distance_km = serializers.SerializerMethodField()
    available_days = serializers.SerializerMethodField()

    class Meta:
        model = WorkerProfile
        fields = [
            "id", "username", "bio", "years_experience",
            "has_diploma", "bevoegdheid",
            "service_types", "contract_types", "hourly_rate",
            "city", "work_radius_km",
            "is_available", "immediate_available", "hours_per_week",
            "available_days", "distance_km",
        ]

    def get_distance_km(self, obj):
        if hasattr(obj, "distance"):
            return round(obj.distance.km, 2)
        return None

    def get_available_days(self, obj):
        avail = obj.availability or {}
        return avail.get("days", [])
