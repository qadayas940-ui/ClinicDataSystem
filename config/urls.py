"""مسارات URL الرئيسية للمشروع."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("patients/", include("apps.patients.urls")),
    path("visits/", include("apps.visits.urls")),
    path("laboratory/", include("apps.laboratory.urls")),
    path("referrals/", include("apps.referrals.urls")),
    path("ophthalmology/", include("apps.ophthalmology.urls")),
    path("importer/", include("apps.importer.urls")),
    path("backup/", include("apps.backup.urls")),
    path("updates/", include("apps.updater.urls")),
]
