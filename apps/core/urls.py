"""مسارات تطبيق النواة."""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/health/", views.health_check, name="health_api"),
    path("health/", views.health_check_page, name="health_page"),
]
