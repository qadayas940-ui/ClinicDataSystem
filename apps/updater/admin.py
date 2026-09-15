"""لوحة إدارة التحديثات."""
from django.contrib import admin

from .models import UpdateManifest


@admin.register(UpdateManifest)
class UpdateManifestAdmin(admin.ModelAdmin):
    list_display = ("version", "channel", "update_type", "is_mandatory", "checked_at")
    list_filter = ("channel", "update_type", "is_mandatory")
