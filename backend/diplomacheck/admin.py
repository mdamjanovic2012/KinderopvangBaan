from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Diploma


@admin.register(Diploma)
class DiplomaAdmin(ModelAdmin):
    list_display = ["name", "level", "crebo", "is_active"]
    list_filter = ["level", "is_active"]
    search_fields = ["name", "crebo"]
    list_editable = ["is_active"]
