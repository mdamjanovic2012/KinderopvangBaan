from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from .models import WorkerProfile
from .serializers import UserSerializer, RegisterSerializer, WorkerProfileSerializer, PublicWorkerSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class WorkerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, _ = WorkerProfile.objects.get_or_create(user=request.user)
        return Response(WorkerProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = WorkerProfile.objects.get_or_create(user=request.user)
        serializer = WorkerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class WorkerListView(APIView):
    """
    Public list of available workers.
    GET /api/users/workers/?lat=52.37&lng=4.89&radius=15
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = WorkerProfile.objects.filter(is_available=True).select_related("user")

        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        if lat and lng:
            try:
                point = Point(float(lng), float(lat), srid=4326)
                radius = float(request.query_params.get("radius", 15))
                qs = qs.filter(
                    location__isnull=False,
                    location__distance_lte=(point, D(km=radius)),
                ).annotate(distance=Distance("location", point)).order_by("distance")
            except (ValueError, TypeError):
                pass

        serializer = PublicWorkerSerializer(qs, many=True)
        return Response(serializer.data)
