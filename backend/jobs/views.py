import hashlib

from django.db.models import Q
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D

from .models import Company, Job, VacatureClick
from .serializers import CompanySerializer, JobSerializer, JobMapPinSerializer, VacatureClickSerializer
from .constants import CAO_FUNCTIONS

GUEST_JOB_LIMIT = 3


def _apply_job_filters(qs, params):
    """Apply common job filters from query params to a queryset."""
    if params.get("job_type"):
        qs = qs.filter(job_type=params["job_type"])
    if params.get("contract_type"):
        qs = qs.filter(contract_type=params["contract_type"])
    if params.get("city"):
        qs = qs.filter(city__icontains=params["city"])
    if params.get("requires_diploma") in ("true", "false"):
        qs = qs.filter(requires_diploma=params["requires_diploma"] == "true")
    if params.get("requires_vog") in ("true", "false"):
        qs = qs.filter(requires_vog=params["requires_vog"] == "true")
    hours_min = params.get("hours_min", "")
    if str(hours_min).isdigit():
        qs = qs.filter(hours_max__gte=int(hours_min))
    hours_max = params.get("hours_max", "")
    if str(hours_max).isdigit():
        qs = qs.filter(hours_min__lte=int(hours_max))
    if params.get("search"):
        q = params["search"]
        qs = qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) |
            Q(city__icontains=q) | Q(location_name__icontains=q) |
            Q(company__name__icontains=q)
        )
    return qs


class JobListView(generics.ListAPIView):
    serializer_class = JobSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = (
            Job.objects
            .filter(is_active=True, is_expired=False)
            .select_related("company")
            .order_by("-created_at")
        )
        return _apply_job_filters(qs, self.request.query_params)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()

        is_authenticated = request.user and request.user.is_authenticated
        if not is_authenticated:
            queryset = queryset[:GUEST_JOB_LIMIT]

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "total": total,
            "shown": len(serializer.data),
            "blurred": not is_authenticated and total > GUEST_JOB_LIMIT,
            "results": serializer.data,
        })


class JobDetailView(generics.RetrieveAPIView):
    serializer_class = JobSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    queryset = Job.objects.filter(is_active=True, is_expired=False).select_related("company")


class NearbyJobsView(APIView):
    """
    GET /api/jobs/nearby/?lat=52.37&lng=4.89&radius=15&job_type=bso
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError):
            return Response({"error": "lat en lng zijn verplicht."}, status=400)

        radius = float(request.query_params.get("radius", 15))

        point = Point(lng, lat, srid=4326)
        qs = (
            Job.objects
            .filter(is_active=True, is_expired=False, location__distance_lte=(point, D(km=radius)))
            .annotate(distance=Distance("location", point))
            .order_by("distance")
            .select_related("company")
        )
        qs = _apply_job_filters(qs, request.query_params)

        is_authenticated = request.user and request.user.is_authenticated
        total = qs.count()
        if not is_authenticated:
            qs = qs[:GUEST_JOB_LIMIT]

        return Response({
            "total": total,
            "shown": qs.count() if is_authenticated else min(total, GUEST_JOB_LIMIT),
            "blurred": not is_authenticated and total > GUEST_JOB_LIMIT,
            "results": JobSerializer(qs, many=True).data,
        })


class JobClickView(APIView):
    """
    POST /api/jobs/{pk}/click/
    Registreert een klik en geeft de source_url terug voor redirect.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        try:
            job = Job.objects.get(pk=pk, is_active=True, is_expired=False)
        except Job.DoesNotExist:
            return Response({"error": "Vacature niet gevonden."}, status=404)

        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
        ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else ""

        user = request.user if request.user.is_authenticated else None
        VacatureClick.objects.create(job=job, user=user, ip_hash=ip_hash)

        return Response({"source_url": job.source_url})


class JobChoicesView(APIView):
    """
    GET /api/jobs/choices/
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "cao_functions": [{"value": v, "label": l} for v, l in CAO_FUNCTIONS],
            "contract_types": [
                {"value": "fulltime", "label": "Full-time"},
                {"value": "parttime", "label": "Part-time"},
                {"value": "temp", "label": "Tijdelijk"},
            ],
        })


class CompanyListView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        companies = Company.objects.filter(is_active=True)
        return Response(CompanySerializer(companies, many=True).data)


class JobMapPinsView(APIView):
    """
    GET /api/jobs/map-pins/
    Lichtgewicht endpoint voor kaartpinnen — alleen jobs met locatie.
    Gasten zien een beperkt aantal pinnen; ingelogde gebruikers alles.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = (
            Job.objects
            .filter(is_active=True, is_expired=False, location__isnull=False)
            .select_related("company")
        )
        qs = _apply_job_filters(qs, request.query_params)

        is_authenticated = request.user and request.user.is_authenticated
        total = qs.count()
        if not is_authenticated:
            qs = qs[:GUEST_JOB_LIMIT * 10]  # toon beperkt aantal pinnen voor gasten

        return Response({
            "total": total,
            "blurred": not is_authenticated and total > GUEST_JOB_LIMIT * 10,
            "results": JobMapPinSerializer(qs, many=True).data,
        })
