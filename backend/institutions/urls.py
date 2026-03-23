from django.urls import path
from . import views

urlpatterns = [
    path("", views.InstitutionListView.as_view(), name="institution_list"),
    path("map-pins/", views.MapPinsView.as_view(), name="map_pins"),
    path("<int:pk>/", views.InstitutionDetailView.as_view(), name="institution_detail"),
    path("nearby/", views.NearbyInstitutionsView.as_view(), name="nearby_institutions"),
    path("<int:pk>/reviews/", views.ReviewListView.as_view(), name="reviews"),
]
