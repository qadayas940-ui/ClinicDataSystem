"""معالجات السياق (Context Processors) لإتاحة معلومات التطبيق في القوالب."""
from django.conf import settings
from django.utils import timezone


def app_info(request):
    """يوفّر اسم التطبيق وإصداره واسم المنشأة لكل القوالب."""
    trial = None
    if getattr(request, "user", None) and request.user.is_authenticated:
        from .models import LicenseState

        trial = LicenseState.objects.first()
        if trial and trial.expires_at and trial.expires_at <= timezone.now() and trial.mode != "licensed":
            trial.mode = "read_only"
            trial.is_expired = True
    unread_notifications = 0
    recent_notifications = []
    if getattr(request, "user", None) and request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(read_at__isnull=True).count()
        recent_notifications = request.user.notifications.all()[:6]
    language = getattr(request, "LANGUAGE_CODE", "ar") or "ar"
    return {
        "APP_NAME": getattr(settings, "APP_NAME", "نظام العيادة"),
        "APP_VERSION": getattr(settings, "APP_VERSION", "1.0.0"),
        "FACILITY_NAME": getattr(settings, "FACILITY_NAME", "العيادة"),
        "LICENSE_STATE": trial,
        "UI_LANG": language,
        "UI_DIR": "rtl" if language.startswith("ar") else "ltr",
        "UNREAD_NOTIFICATIONS": unread_notifications,
        "RECENT_NOTIFICATIONS": recent_notifications,
    }
