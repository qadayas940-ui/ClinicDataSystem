"""إعدادات لوحة الإدارة لتطبيق الحسابات."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Permission, Role, RolePermission, StaffProfile, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_system_role")
    search_fields = ("name", "code")


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "category")
    search_fields = ("name", "code")
    list_filter = ("category",)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "department", "is_active", "is_locked")
    list_filter = ("role", "department", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("معلومات العيادة", {"fields": ("role", "department", "is_force_password_change", "failed_login_attempts", "locked_until", "last_login_ip")}),
    )

    @admin.display(boolean=True, description="مقفل")
    def is_locked(self, obj):
        return obj.is_locked


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "phone", "specialization")
    search_fields = ("display_name", "phone")
