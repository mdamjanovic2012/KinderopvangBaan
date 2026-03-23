from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from .models import Job, JobApplication
from .serializers import JobSerializer, JobApplicationSerializer


class JobListView(generics.ListAPIView):
    serializer_class = JobSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["job_type", "contract_type", "city", "is_active"]
    search_fields = ["title", "description", "city"]

    def get_queryset(self):
        return Job.objects.filter(is_active=True).select_related("institution")


class JobDetailView(generics.RetrieveAPIView):
    serializer_class = JobSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Job.objects.filter(is_active=True)


class NearbyJobsView(APIView):
    """
    GET /api/jobs/nearby/?lat=52.37&lng=4.89&radius=15&type=bso
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError):
            return Response({"error": "lat and lng required."}, status=400)

        radius = float(request.query_params.get("radius", 15))
        job_type = request.query_params.get("type")

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
    def post(self, request, pk):
        job = Job.objects.get(pk=pk, is_active=True)
        serializer = JobApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(job=job, applicant=request.user)
        return Response(serializer.data, status=201)


class MyApplicationsView(generics.ListAPIView):
    serializer_class = JobApplicationSerializer

    def get_queryset(self):
        return JobApplication.objects.filter(applicant=self.request.user).select_related("job")
