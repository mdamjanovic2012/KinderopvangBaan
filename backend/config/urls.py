from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("pivce-za-zivce/", admin.site.urls),
    path("api/health/", health, name="health"),

    # Auth
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/", include("users.urls")),

    # Core
    path("api/jobs/", include("jobs.urls")),
    path("api/users/", include("users.urls")),
    path("api/diplomacheck/", include("diplomacheck.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
