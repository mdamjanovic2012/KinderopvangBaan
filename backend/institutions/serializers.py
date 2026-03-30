from rest_framework import serializers
from .models import Institution, Review


class InstitutionSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = [
            "id", "name", "institution_type", "description",
            "street", "house_number", "postcode", "city", "province",
            "phone", "email", "website",
            "capacity", "available_spots", "opening_hours",
            "lrk_number", "lrk_verified", "lrk_url",
            "kvk_nummer_houder", "naam_houder", "gemeente",
            "parent",
            "is_claimed",
            "distance_km", "avg_rating",
            "location",
        ]

    def get_location(self, obj):
        if obj.location is None:
            return None
        return {"type": "Point", "coordinates": [obj.location.x, obj.location.y]}

    def get_distance_km(self, obj):
        if hasattr(obj, "distance"):
            return round(obj.distance.km, 2)
        return None

    def get_avg_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)


class InstitutionPinSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = ["id", "name", "institution_type", "city", "lrk_verified", "location"]

    def get_location(self, obj):
        if obj.location is None:
            return None
        return {"type": "Point", "coordinates": [obj.location.x, obj.location.y]}


class InstitutionDetailSerializer(InstitutionSerializer):
    """
    Uitgebreide serializer voor de detailpagina — bevat moeder-dochter structuur.
    """
    parent_info = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()

    class Meta(InstitutionSerializer.Meta):
        fields = InstitutionSerializer.Meta.fields + ["parent_info", "locations"]

    def get_parent_info(self, obj):
        if not obj.parent_id:
            return None
        parent = obj.parent
        return {
            "id": parent.id,
            "name": parent.name,
            "naam_houder": parent.naam_houder,
            "city": parent.city,
            "institution_type": parent.institution_type,
        }

    def get_locations(self, obj):
        """
        Als deze instelling een kind is → geef alle locaties van de moeder terug.
        Als deze instelling een moeder is → geef alle kinderen terug.
        """
        if obj.parent_id:
            sibling_qs = obj.parent.children.exclude(pk=obj.pk).filter(is_active=True)
        else:
            sibling_qs = obj.children.filter(is_active=True)

        result = []
        for loc in sibling_qs:
            result.append({
                "id": loc.id,
                "name": loc.name,
                "city": loc.city,
                "institution_type": loc.institution_type,
                "active_job_count": 0,
            })
        return result


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "author_name", "rating", "text", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]
