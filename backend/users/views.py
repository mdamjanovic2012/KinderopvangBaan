from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import WorkerProfile
from .serializers import UserSerializer, RegisterSerializer, WorkerProfileSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class WorkerProfileView(APIView):
    def get(self, request):
        profile, _ = WorkerProfile.objects.get_or_create(user=request.user)
        return Response(WorkerProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = WorkerProfile.objects.get_or_create(user=request.user)
        serializer = WorkerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
