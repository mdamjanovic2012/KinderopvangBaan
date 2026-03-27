from django.urls import path
from . import views

urlpatterns = [
    path("search/", views.DiplomaSearchView.as_view(), name="diploma_search"),
    path("<int:pk>/", views.DiplomaDetailView.as_view(), name="diploma_detail"),
]
