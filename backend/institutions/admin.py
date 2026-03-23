from django.contrib import admin
from .models import Institution, Review


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name", "institution_type", "city", "lrk_verified", "is_active", "is_claimed"]
    list_filter = ["institution_type", "city", "lrk_verified", "is_active"]
    search_fields = ["name", "city", "postcode", "lrk_number"]
    list_editable = ["lrk_verified", "is_active"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["institution", "author", "rating", "created_at"]
