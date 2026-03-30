from django.contrib.gis.db import models as gis_models
from django.db import models
from django.conf import settings
from .constants import CAO_FUNCTIONS


class Company(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    website = models.URLField(blank=True)
    job_board_url = models.URLField()
    scraper_class = models.CharField(max_length=100, help_text="bijv. KinderdamScraper")
    logo_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class GeocodedLocation(models.Model):
    """DB-level cache van PDOK geocoding resultaten (per unieke location_name)."""
    location_name = models.CharField(max_length=255, unique=True)
    city = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    location = gis_models.PointField(null=True, blank=True)
    geocoded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["location_name"]

    def __str__(self):
        return f"{self.location_name} → {self.city}"


class Job(gis_models.Model):
    TYPE_CHOICES = CAO_FUNCTIONS

    CONTRACT_FULLTIME = "fulltime"
    CONTRACT_PARTTIME = "parttime"
    CONTRACT_TEMP = "temp"
    CONTRACT_CHOICES = [
        (CONTRACT_FULLTIME, "Full-time"),
        (CONTRACT_PARTTIME, "Part-time"),
        (CONTRACT_TEMP, "Tijdelijk"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="jobs")

    title = models.CharField(max_length=255)
    job_type = models.CharField(max_length=30, choices=TYPE_CHOICES, blank=True)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_CHOICES, blank=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)

    # Locatie van de specifieke kinderopvang locatie
    location_name = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    location = gis_models.PointField(null=True, blank=True)

    # Beloning
    salary_min = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    hours_min = models.PositiveSmallIntegerField(null=True, blank=True)
    hours_max = models.PositiveSmallIntegerField(null=True, blank=True)

    # Doelgroep kinderen
    age_min = models.PositiveSmallIntegerField(null=True, blank=True)
    age_max = models.PositiveSmallIntegerField(null=True, blank=True)

    # Vereisten
    requires_vog = models.BooleanField(default=True)
    requires_diploma = models.BooleanField(default=False)
    requires_bevoegdheid = models.JSONField(default=list, blank=True)
    min_experience = models.PositiveSmallIntegerField(null=True, blank=True)

    # Scraping metadata
    source_url = models.URLField(unique=True)
    external_id = models.CharField(max_length=255, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_expired = models.BooleanField(default=False, db_index=True)

    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.company.name}"


class VacatureClick(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="clicks")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="vacature_clicks",
    )
    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-clicked_at"]

    def __str__(self):
        return f"Click: {self.job.title} @ {self.clicked_at:%Y-%m-%d %H:%M}"
