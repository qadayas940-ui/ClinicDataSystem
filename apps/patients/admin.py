"""لوحة إدارة المرضى."""
from django.contrib import admin

from .models import Patient, PatientAddress, PatientContact, PatientName


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("internal_code", "gender", "is_active", "created_at")
    list_filter = ("gender", "is_active")
    search_fields = ("internal_code",)


admin.site.register(PatientName)
admin.site.register(PatientContact)
admin.site.register(PatientAddress)
