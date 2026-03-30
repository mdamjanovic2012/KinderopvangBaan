from django.urls import path
from . import views

urlpatterns = [
    path("", views.JobListView.as_view(), name="job_list"),
    path("<int:pk>/", views.JobDetailView.as_view(), name="job_detail"),
    path("<int:pk>/click/", views.JobClickView.as_view(), name="job_click"),
    path("nearby/", views.NearbyJobsView.as_view(), name="nearby_jobs"),
    path("choices/", views.JobChoicesView.as_view(), name="job_choices"),
    path("companies/", views.CompanyListView.as_view(), name="company_list"),
]
