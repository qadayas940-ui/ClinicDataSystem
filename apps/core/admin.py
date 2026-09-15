"""لوحة إدارة النواة."""
from django.contrib import admin

from .models import (
    AppVersion,
    AuditLog,
    BackupHistory,
    Department,
    LicenseState,
    ReferenceValue,
    ServerSettings,
    UpdateHistory,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")


@admin.register(ReferenceValue)
class ReferenceValueAdmin(admin.ModelAdmin):
    list_display = ("canonical_name", "category", "occurrence_count", "needs_review", "is_active")
    list_filter = ("category", "needs_review", "is_active")
    search_fields = ("canonical_name", "normalized_name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "model_name", "object_repr", "ip_address")
    list_filter = ("action", "timestamp")
    search_fields = ("object_repr", "model_name")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(AppVersion)
class AppVersionAdmin(admin.ModelAdmin):
    list_display = ("version_number", "channel", "is_current", "release_date")


@admin.register(UpdateHistory)
class UpdateHistoryAdmin(admin.ModelAdmin):
    list_display = ("from_version", "to_version", "update_type", "status", "started_at")


@admin.register(LicenseState)
class LicenseStateAdmin(admin.ModelAdmin):
    list_display = ("mode", "is_trial", "is_expired", "expires_at")


@admin.register(BackupHistory)
class BackupHistoryAdmin(admin.ModelAdmin):
    list_display = ("backup_type", "status", "created_at", "created_by")
    list_filter = ("status", "backup_type")


@admin.register(ServerSettings)
class ServerSettingsAdmin(admin.ModelAdmin):
    list_display = ("bind_address", "port", "allow_network_access")
