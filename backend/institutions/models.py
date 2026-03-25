from django.contrib.gis.db import models
from django.conf import settings


class Institution(models.Model):
    TYPE_BSO = "bso"
    TYPE_KDV = "kdv"
    TYPE_GASTOUDER = "gastouder"
    TYPE_PEUTERSPEELZAAL = "peuterspeelzaal"
    TYPE_CHOICES = [
        (TYPE_BSO, "BSO"),
        (TYPE_KDV, "KDV / Kinderdagverblijf"),
        (TYPE_GASTOUDER, "Gastouderbureau"),
        (TYPE_PEUTERSPEELZAAL, "Peuterspeelzaal"),
    ]

    # Basic info
    name = models.CharField(max_length=255)
    institution_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Address
    street = models.CharField(max_length=255, blank=True)
    house_number = models.CharField(max_length=10, blank=True)
    postcode = models.CharField(max_length=10)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100, blank=True)

    # GeoDjango — core voor de kaart
    location = models.PointField()

    # Capacity & availability
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    available_spots = models.PositiveSmallIntegerField(null=True, blank=True)

    # Opening hours (simple JSON: {"mon": "07:00-18:30", "tue": "07:00-18:30", ...})
    opening_hours = models.JSONField(default=dict, blank=True)

    # LRK registration (Landelijk Register Kinderopvang)
    lrk_number = models.CharField(max_length=50, blank=True, unique=True, null=True)
    lrk_verified = models.BooleanField(default=False)
    lrk_url = models.URLField(blank=True)

    # Houder / parent organisation (from LRK)
    kvk_nummer_houder = models.CharField(max_length=20, blank=True)
    naam_houder = models.CharField(max_length=255, blank=True)
    gemeente = models.CharField(max_length=100, blank=True)

    # Parent-child structure (moeder-dochter)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="children",
    )

    # Linked account (if institution manages their own profile)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="owned_institutions",
    )

    # Meta
    is_active = models.BooleanField(default=True)
    is_claimed = models.BooleanField(default=False)  # institution has taken ownership
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.institution_type}) — {self.city}"


class Review(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # 1-5
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("institution", "author")

    def __str__(self):
        return f"Review {self.rating}/5 for {self.institution.name}"
