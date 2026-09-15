"""لوحة إدارة عيادة العيون."""
from django.contrib import admin

from .models import EyeClinicVisit


@admin.register(EyeClinicVisit)
class EyeClinicVisitAdmin(admin.ModelAdmin):
    list_display = ("patient", "visit_date", "status", "doctor")
    list_filter = ("status",)
