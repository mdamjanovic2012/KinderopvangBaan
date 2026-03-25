from django.contrib.gis.db import models
from django.conf import settings
from institutions.models import Institution
from .constants import CAO_FUNCTIONS


class Job(models.Model):
    # CAO kinderopvang functielijst (vervangt TYPE_CHOICES)
    TYPE_CHOICES = CAO_FUNCTIONS

    CONTRACT_FULLTIME = "fulltime"
    CONTRACT_PARTTIME = "parttime"
    CONTRACT_TEMP = "temp"
    CONTRACT_CHOICES = [
        (CONTRACT_FULLTIME, "Full-time"),
        (CONTRACT_PARTTIME, "Part-time"),
        (CONTRACT_TEMP, "Tijdelijk"),
    ]

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="jobs")
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posted_jobs",
    )

    title = models.CharField(max_length=255)
    job_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_CHOICES)
    description = models.TextField()

    # Location inherited from institution but stored for geo queries
    location = models.PointField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Compensation
    salary_min = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    hours_per_week = models.PositiveSmallIntegerField(null=True, blank=True)

    # Requirements
    requires_vog = models.BooleanField(default=True)
    requires_diploma = models.BooleanField(default=False)
    # e.g. ["dagopvang", "bso", "peuterspeelzaal"]
    requires_bevoegdheid = models.JSONField(default=list, blank=True)
    min_experience = models.PositiveSmallIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)  # paid listing

    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.institution.name}"


class JobApplication(models.Model):
    STATUS_PENDING = "pending"
    STATUS_VIEWED = "viewed"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "In behandeling"),
        (STATUS_VIEWED, "Bekeken"),
        (STATUS_ACCEPTED, "Geaccepteerd"),
        (STATUS_REJECTED, "Afgewezen"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("job", "applicant")

    def __str__(self):
        return f"{self.applicant.username} → {self.job.title}"
