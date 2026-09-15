"""لوحة إدارة الزيارات."""
from django.contrib import admin

from .models import Visit, VisitService


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("patient", "visit_date", "status", "doctor")
    list_filter = ("status",)


admin.site.register(VisitService)
