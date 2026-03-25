from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Job, JobApplication


@admin.register(Job)
class JobAdmin(ModelAdmin):
    list_display = [
        "title", "institution", "job_type", "contract_type",
        "city", "hours_per_week", "is_active", "is_premium", "created_at",
    ]
    list_filter = ["job_type", "contract_type", "is_active", "is_premium"]
    search_fields = ["title", "city", "institution__name", "institution__naam_houder"]
    readonly_fields = ["created_at", "updated_at", "posted_by"]
    ordering = ["-created_at"]

    fieldsets = [
        ("Vacature", {
            "fields": ["title", "institution", "posted_by", "job_type", "contract_type", "description"],
        }),
        ("Details", {
            "fields": ["city", "hours_per_week", "salary_min", "salary_max"],
        }),
        ("Vereisten", {
            "fields": ["requires_vog", "requires_diploma"],
        }),
        ("Status", {
            "fields": ["is_active", "is_premium", "expires_at"],
        }),
        ("Tijdstempels", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    actions = ["activate_jobs", "deactivate_jobs", "mark_premium", "unmark_premium"]

    @admin.action(description="Activeer geselecteerde vacatures")
    def activate_jobs(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactiveer geselecteerde vacatures")
    def deactivate_jobs(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Markeer als premium")
    def mark_premium(self, request, queryset):
        queryset.update(is_premium=True)

    @admin.action(description="Verwijder premium status")
    def unmark_premium(self, request, queryset):
        queryset.update(is_premium=False)


@admin.register(JobApplication)
class JobApplicationAdmin(ModelAdmin):
    list_display = ["applicant", "job", "job_institution", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["applicant__username", "applicant__email", "job__title", "job__institution__name"]
    readonly_fields = ["applicant", "job", "cover_letter", "created_at"]
    ordering = ["-created_at"]

    actions = ["mark_viewed", "mark_accepted", "mark_rejected"]

    def job_institution(self, obj):
        return obj.job.institution.name
    job_institution.short_description = "Organisatie"

    @admin.action(description="Markeer als bekeken")
    def mark_viewed(self, request, queryset):
        queryset.update(status=JobApplication.STATUS_VIEWED)

    @admin.action(description="Markeer als geaccepteerd")
    def mark_accepted(self, request, queryset):
        queryset.update(status=JobApplication.STATUS_ACCEPTED)

    @admin.action(description="Markeer als afgewezen")
    def mark_rejected(self, request, queryset):
        queryset.update(status=JobApplication.STATUS_REJECTED)
