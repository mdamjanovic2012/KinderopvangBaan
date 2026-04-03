from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Branch, Company, GeocodedLocation, Job, VacatureClick


@admin.register(Company)
class CompanyAdmin(ModelAdmin):
    list_display = ["name", "scraper_class", "is_active", "last_scraped_at", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "scraper_class"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["last_scraped_at", "created_at", "updated_at"]

    fieldsets = [
        ("Bedrijf", {
            "fields": ["name", "slug", "website", "logo_url", "description"],
        }),
        ("Scraping", {
            "fields": ["job_board_url", "scraper_class", "is_active", "last_scraped_at"],
        }),
        ("Tijdstempels", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


@admin.register(GeocodedLocation)
class GeocodedLocationAdmin(ModelAdmin):
    list_display = ["location_name", "city", "postcode", "municipality", "geocoded_at"]
    search_fields = ["location_name", "city", "postcode", "municipality"]
    readonly_fields = ["geocoded_at"]


@admin.register(Job)
class JobAdmin(ModelAdmin):
    list_display = [
        "title", "company", "job_type", "contract_type",
        "city", "hours_min", "hours_max", "is_active", "is_expired", "is_premium", "created_at",
    ]
    list_filter = ["company", "job_type", "contract_type", "is_active", "is_expired", "is_premium"]
    search_fields = ["title", "city", "location_name", "company__name"]
    readonly_fields = ["created_at", "updated_at", "last_seen_at", "source_url", "external_id"]
    ordering = ["-created_at"]

    fieldsets = [
        ("Vacature", {
            "fields": ["title", "company", "job_type", "contract_type", "short_description", "description"],
        }),
        ("Locatie", {
            "fields": ["location_name", "city", "postcode", "location"],
        }),
        ("Details", {
            "fields": ["hours_min", "hours_max", "salary_min", "salary_max", "age_min", "age_max"],
        }),
        ("Vereisten", {
            "fields": ["requires_vog", "requires_diploma", "requires_bevoegdheid", "min_experience"],
        }),
        ("Status", {
            "fields": ["is_active", "is_expired", "is_premium", "expires_at"],
        }),
        ("Scraping", {
            "fields": ["source_url", "external_id", "last_seen_at"],
            "classes": ["collapse"],
        }),
        ("Tijdstempels", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    actions = ["activate_jobs", "deactivate_jobs", "mark_expired", "mark_premium", "unmark_premium"]

    @admin.action(description="Activeer geselecteerde vacatures")
    def activate_jobs(self, request, queryset):
        queryset.update(is_active=True, is_expired=False)

    @admin.action(description="Deactiveer geselecteerde vacatures")
    def deactivate_jobs(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Markeer als verlopen")
    def mark_expired(self, request, queryset):
        queryset.update(is_expired=True, is_active=False)

    @admin.action(description="Markeer als premium")
    def mark_premium(self, request, queryset):
        queryset.update(is_premium=True)

    @admin.action(description="Verwijder premium status")
    def unmark_premium(self, request, queryset):
        queryset.update(is_premium=False)


@admin.register(Branch)
class BranchAdmin(ModelAdmin):
    list_display = ["name", "company_slug", "street", "postcode", "city", "geocoded_at"]
    list_filter = ["company_slug"]
    search_fields = ["name", "city", "postcode", "company_slug"]
    readonly_fields = ["geocoded_at", "created_at", "updated_at"]
    ordering = ["company_slug", "name"]


@admin.register(VacatureClick)
class VacatureClickAdmin(ModelAdmin):
    list_display = ["job", "user", "clicked_at", "ip_hash"]
    list_filter = ["clicked_at"]
    search_fields = ["job__title", "user__username", "user__email"]
    readonly_fields = ["job", "user", "clicked_at", "ip_hash"]
    ordering = ["-clicked_at"]
