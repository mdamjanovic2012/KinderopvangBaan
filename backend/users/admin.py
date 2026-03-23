from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, WorkerProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "email", "role", "is_active"]
    list_filter = ["role", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("Role & Contact", {"fields": ("role", "phone", "avatar")}),
    )


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "city", "is_available", "vog_verified", "is_premium"]
    list_filter = ["is_available", "vog_verified", "is_premium"]
