"""مسارات تطبيق النواة."""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/health/", views.health_check, name="health_api"),
    path("health/", views.health_check_page, name="health_page"),
    path("departments/", views.department_list, name="departments"),
    path("departments/new/", views.department_form, name="department_create"),
    path("departments/<int:pk>/edit/", views.department_form, name="department_edit"),
    path("departments/<int:pk>/archive/", views.department_archive, name="department_archive"),
    path("server-settings/", views.server_settings, name="server_settings"),
]
