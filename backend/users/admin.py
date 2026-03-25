from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin

from .models import User, WorkerProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    list_display = ["username", "email", "role", "is_active", "is_staff", "date_joined"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = UserAdmin.fieldsets + (
        ("Rol & Contact", {"fields": ("role", "phone", "avatar")}),
    )

    actions = ["activate_users", "deactivate_users"]

    @admin.action(description="Activeer geselecteerde gebruikers")
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactiveer geselecteerde gebruikers")
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(WorkerProfile)
class WorkerProfileAdmin(ModelAdmin):
    list_display = ["user", "city", "work_radius_km", "is_available", "vog_verified", "has_diploma", "is_premium"]
    list_filter = ["is_available", "vog_verified", "has_diploma", "is_premium"]
    search_fields = ["user__username", "user__email", "city"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = [
        ("Gebruiker", {
            "fields": ["user"],
        }),
        ("Profiel", {
            "fields": ["bio", "years_experience", "service_types", "contract_types", "hourly_rate"],
        }),
        ("Locatie & Beschikbaarheid", {
            "fields": ["city", "work_radius_km", "availability", "is_available"],
        }),
        ("Compliance", {
            "fields": ["has_vog", "vog_verified", "has_diploma", "diploma_verified"],
        }),
        ("Status", {
            "fields": ["is_premium"],
        }),
        ("Tijdstempels", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
