from rest_framework import serializers
from .models import Institution, Review


class InstitutionSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = [
            "id", "name", "institution_type", "description",
            "street", "house_number", "postcode", "city", "province",
            "phone", "email", "website",
            "capacity", "available_spots", "opening_hours",
            "lrk_number", "lrk_verified",
            "is_claimed",
            "distance_km", "avg_rating",
            # location as GeoJSON
            "location",
        ]

    def get_distance_km(self, obj):
        if hasattr(obj, "distance"):
            return round(obj.distance.km, 2)
        return None

    def get_avg_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "author_name", "rating", "text", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]
