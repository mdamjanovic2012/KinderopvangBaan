from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("me/", views.MeView.as_view(), name="me"),
    path("worker-profile/", views.WorkerProfileView.as_view(), name="worker_profile"),
    path("workers/", views.WorkerListView.as_view(), name="worker_list"),
]
