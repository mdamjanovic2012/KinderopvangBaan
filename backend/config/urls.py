import os

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponseRedirect
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def health(request):
    return JsonResponse({"status": "ok"})


def airflow_redirect(request):
    """Redirect naar de Airflow webserver (ACI). Alleen voor superusers."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    airflow_url = os.environ.get("AIRFLOW_URL", "")
    if not airflow_url:
        return JsonResponse({"detail": "AIRFLOW_URL not configured"}, status=503)
    return HttpResponseRedirect(airflow_url)


urlpatterns = [
    path("pivce-za-zivce/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("airflow/", airflow_redirect, name="airflow_redirect"),

    # Auth
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/", include("users.urls")),

    # Core
    path("api/jobs/", include("jobs.urls")),
    path("api/users/", include("users.urls")),
    path("api/diplomacheck/", include("diplomacheck.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
