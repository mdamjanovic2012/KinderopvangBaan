from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from institutions.models import Institution
from .models import Job, JobApplication
from .serializers import JobSerializer, JobApplicationSerializer


class JobListCreateView(generics.ListCreateAPIView):
    serializer_class = JobSerializer
    filterset_fields = ["job_type", "contract_type", "city", "is_active"]
    search_fields = ["title", "description", "city"]

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return Job.objects.filter(is_active=True).select_related("institution")

    def perform_create(self, serializer):
        institution = serializer.validated_data["institution"]
        # Copy location from institution if not supplied
        location = serializer.validated_data.get("location") or institution.location
        city = serializer.validated_data.get("city") or institution.city
        serializer.save(posted_by=self.request.user, location=location, city=city)


class JobDetailView(generics.RetrieveAPIView):
    serializer_class = JobSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    queryset = Job.objects.filter(is_active=True)


class NearbyJobsView(APIView):
    """
    GET /api/jobs/nearby/?lat=52.37&lng=4.89&radius=15&type=bso
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError):
            return Response({"error": "lat and lng required."}, status=400)

        radius = float(request.query_params.get("radius", 15))
        job_type = request.query_params.get("job_type")

        point = Point(lng, lat, srid=4326)
        qs = Job.objects.filter(
            is_active=True,
            location__distance_lte=(point, D(km=radius)),
        ).annotate(
            distance=Distance("location", point)
        ).order_by("distance").select_related("institution")

        if job_type:
            qs = qs.filter(job_type=job_type)

        return Response(JobSerializer(qs, many=True).data)


class ApplyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            job = Job.objects.get(pk=pk, is_active=True)
        except Job.DoesNotExist:
            return Response({"error": "Vacature niet gevonden."}, status=404)
        serializer = JobApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(job=job, applicant=request.user)
        return Response(serializer.data, status=201)


class MyApplicationsView(generics.ListAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JobApplication.objects.filter(applicant=self.request.user).select_related("job")
