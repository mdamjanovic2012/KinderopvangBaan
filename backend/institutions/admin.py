from django.contrib import admin
from django.db.models import Count, Avg
from unfold.admin import ModelAdmin, TabularInline

from .models import Institution, Review


class ReviewInline(TabularInline):
    model = Review
    extra = 0
    readonly_fields = ["author", "rating", "text", "created_at"]
    can_delete = False


@admin.register(Institution)
class InstitutionAdmin(ModelAdmin):
    list_display = [
        "name", "institution_type", "city", "lrk_verified",
        "is_claimed", "is_active", "job_count", "avg_rating_display",
    ]
    list_filter = ["institution_type", "lrk_verified", "is_claimed", "is_active", "province"]
    search_fields = ["name", "city", "postcode", "lrk_number", "naam_houder", "kvk_nummer_houder"]
    readonly_fields = ["created_at", "updated_at", "lrk_number"]
    ordering = ["name"]

    fieldsets = [
        ("Basisgegevens", {
            "fields": ["name", "institution_type", "description", "is_active", "is_claimed", "owner"],
        }),
        ("Adres", {
            "fields": ["street", "house_number", "postcode", "city", "province"],
        }),
        ("Contact", {
            "fields": ["phone", "email", "website"],
        }),
        ("LRK registratie", {
            "fields": ["lrk_number", "lrk_verified", "lrk_url", "naam_houder", "kvk_nummer_houder", "gemeente"],
        }),
        ("Organisatiestructuur", {
            "fields": ["parent"],
        }),
        ("Capaciteit", {
            "fields": ["capacity", "available_spots", "opening_hours"],
        }),
        ("Tijdstempels", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    inlines = [ReviewInline]
    actions = ["mark_verified", "mark_unverified", "mark_inactive", "mark_active"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _avg_rating=Avg("reviews__rating"),
        )

    def job_count(self, obj):
        return "—"
    job_count.short_description = "Vacatures"

    def avg_rating_display(self, obj):
        if obj._avg_rating is None:
            return "—"
        return f"{obj._avg_rating:.1f} ★"
    avg_rating_display.short_description = "Gem. beoordeling"
    avg_rating_display.admin_order_field = "_avg_rating"

    @admin.action(description="Markeer als LRK-geverifieerd")
    def mark_verified(self, request, queryset):
        queryset.update(lrk_verified=True)

    @admin.action(description="Verwijder LRK-verificatie")
    def mark_unverified(self, request, queryset):
        queryset.update(lrk_verified=False)

    @admin.action(description="Deactiveer organisaties")
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Activeer organisaties")
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ["institution", "author", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["institution__name", "author__username", "text"]
    readonly_fields = ["institution", "author", "rating", "text", "created_at"]
    ordering = ["-created_at"]
