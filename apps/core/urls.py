"""مسارات تطبيق النواة."""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("language/<str:language>/", views.set_language, name="set_language"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/status/", views.notifications_status, name="notifications_status"),
    path("notifications/<int:pk>/open/", views.notification_open, name="notification_open"),
    path("api/health/", views.health_check, name="health_api"),
    path("health/", views.health_check_page, name="health_page"),
    path("departments/", views.department_list, name="departments"),
    path("departments/new/", views.department_form, name="department_create"),
    path("departments/<int:pk>/edit/", views.department_form, name="department_edit"),
    path("departments/<int:pk>/archive/", views.department_archive, name="department_archive"),
    path("departments/<int:pk>/restore/", views.department_restore, name="department_restore"),
    path("server-settings/", views.server_settings, name="server_settings"),
    path("settings/", views.settings_home, name="settings"),
    path("settings/references/", views.reference_list, name="reference_list"),
    path("settings/references/new/", views.reference_form, name="reference_create"),
    path("settings/references/quick-create/", views.reference_quick_create, name="reference_quick_create"),
    path("settings/references/<int:pk>/edit/", views.reference_form, name="reference_edit"),
    path("settings/references/<int:pk>/archive/", views.reference_archive, name="reference_archive"),
    path("settings/references/<int:pk>/restore/", views.reference_restore, name="reference_restore"),
]
