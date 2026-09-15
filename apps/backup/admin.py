"""لوحة إدارة النسخ الاحتياطي."""
from django.contrib import admin

from .models import BackupSchedule


@admin.register(BackupSchedule)
class BackupScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "frequency", "is_enabled", "next_run_at")
    list_filter = ("frequency", "is_enabled")
