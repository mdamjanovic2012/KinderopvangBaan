from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models


class User(AbstractUser):
    ROLE_WORKER = "worker"
    ROLE_INSTITUTION = "institution"
    ROLE_PARENT = "parent"
    ROLE_CHOICES = [
        (ROLE_WORKER, "Worker"),
        (ROLE_INSTITUTION, "Institution"),
        (ROLE_PARENT, "Parent"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_WORKER)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class WorkerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="worker_profile")

    bio = models.TextField(blank=True)
    years_experience = models.PositiveSmallIntegerField(default=0)

    # e.g. ["bso", "nanny"]
    service_types = models.JSONField(default=list)
    # e.g. ["fulltime", "zzp"]
    contract_types = models.JSONField(default=list)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # GeoDjango point (lon, lat)
    location = models.PointField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    work_radius_km = models.PositiveSmallIntegerField(default=15)

    # Compliance
    has_vog = models.BooleanField(default=False)
    vog_verified = models.BooleanField(default=False)
    has_diploma = models.BooleanField(default=False)
    diploma_verified = models.BooleanField(default=False)

    # Availability: {"mon": true, "tue": true, "wed": false, ...}
    availability = models.JSONField(default=dict)

    is_available = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"WorkerProfile: {self.user.username}"
