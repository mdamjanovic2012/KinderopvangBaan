from django.urls import path
from . import views

urlpatterns = [
    path("", views.JobListView.as_view(), name="job_list"),
    path("<int:pk>/", views.JobDetailView.as_view(), name="job_detail"),
    path("<int:pk>/apply/", views.ApplyView.as_view(), name="apply"),
    path("nearby/", views.NearbyJobsView.as_view(), name="nearby_jobs"),
    path("my-applications/", views.MyApplicationsView.as_view(), name="my_applications"),
]
