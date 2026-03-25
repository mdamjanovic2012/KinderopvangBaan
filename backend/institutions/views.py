from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from .models import Institution, Review
from .serializers import InstitutionSerializer, InstitutionDetailSerializer, InstitutionPinSerializer, ReviewSerializer


class InstitutionListView(generics.ListAPIView):
    serializer_class = InstitutionSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["institution_type", "city", "lrk_verified"]
    search_fields = ["name", "city", "postcode"]

    def get_queryset(self):
        return Institution.objects.filter(is_active=True)


class InstitutionDetailView(generics.RetrieveAPIView):
    serializer_class = InstitutionDetailSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    queryset = Institution.objects.filter(is_active=True).select_related("parent").prefetch_related("children", "reviews")


class NearbyInstitutionsView(APIView):
    """
    GET /api/institutions/nearby/?lat=52.37&lng=4.89&radius=10&type=bso
    Returns institutions within `radius` km, ordered by distance.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError):
            return Response({"error": "lat and lng required."}, status=400)

        radius = float(request.query_params.get("radius", 10))
        institution_type = request.query_params.get("type")

        point = Point(lng, lat, srid=4326)
        qs = Institution.objects.filter(
            is_active=True,
            location__distance_lte=(point, D(km=radius)),
        ).annotate(
            distance=Distance("location", point)
        ).order_by("distance")

        if institution_type:
            qs = qs.filter(institution_type=institution_type)

        serializer = InstitutionSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class MapPinsView(APIView):
    """
    GET /api/institutions/map-pins/?type=bso
    Slim endpoint — returns only id, name, institution_type, city, lrk_verified, location.
    No pagination, no heavy fields. Used exclusively by the map component.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Institution.objects.filter(is_active=True, location__isnull=False).only(
            "id", "name", "institution_type", "city", "lrk_verified", "location"
        )
        institution_type = request.query_params.get("type")
        if institution_type:
            qs = qs.filter(institution_type=institution_type)
        return Response(InstitutionPinSerializer(qs, many=True).data)


class ReviewListView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return Review.objects.filter(institution_id=self.kwargs["pk"]).order_by("-created_at")

    def perform_create(self, serializer):
        institution_id = self.kwargs["pk"]
        if Review.objects.filter(institution_id=institution_id, author=self.request.user).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"non_field_errors": ["Je hebt deze instelling al beoordeeld."]})
        serializer.save(author=self.request.user, institution_id=institution_id)
