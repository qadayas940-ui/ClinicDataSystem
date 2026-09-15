"""لوحة إدارة الإحالات."""
from django.contrib import admin

from .models import Referral, ReferralFollowup


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("patient", "destination_name", "referral_date", "status")
    list_filter = ("status",)


admin.site.register(ReferralFollowup)
