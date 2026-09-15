"""لوحة إدارة المختبر."""
from django.contrib import admin

from .models import LabOrder, LabOrderTest


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ("patient", "order_date", "status")
    list_filter = ("status",)


admin.site.register(LabOrderTest)
