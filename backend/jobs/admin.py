from django.contrib import admin
from .models import Job, JobApplication


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["title", "institution", "job_type", "contract_type", "city", "is_active", "is_premium"]
    list_filter = ["job_type", "contract_type", "is_active", "is_premium"]
    search_fields = ["title", "city", "institution__name"]
    list_editable = ["is_active", "is_premium"]


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["applicant", "job", "status", "created_at"]
    list_filter = ["status"]
