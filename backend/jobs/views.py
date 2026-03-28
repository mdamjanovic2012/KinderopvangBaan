import hashlib

from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D

from .models import Company, Job, VacatureClick
from .serializers import CompanySerializer, JobSerializer, VacatureClickSerializer
from .constants import CAO_FUNCTIONS

GUEST_JOB_LIMIT = 3


class JobListView(generics.ListAPIView):
    serializer_class = JobSerializer
    filterset_fields = ["job_type", "contract_type", "city", "is_active", "company"]
    search_fields = ["title", "description", "city", "location_name"]
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Job.objects
            .filter(is_active=True, is_expired=False)
            .select_related("company")
            .order_by("-created_at")
        )

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
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError):
            return Response({"error": "lat en lng zijn verplicht."}, status=400)

        radius = float(request.query_params.get("radius", 15))
        job_type = request.query_params.get("job_type")

        point = Point(lng, lat, srid=4326)
        qs = (
            Job.objects
            .filter(is_active=True, is_expired=False, location__distance_lte=(point, D(km=radius)))
            .annotate(distance=Distance("location", point))
            .order_by("distance")
            .select_related("company")
        )

        if job_type:
            qs = qs.filter(job_type=job_type)

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


class CompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    queryset = Company.objects.filter(is_active=True)
