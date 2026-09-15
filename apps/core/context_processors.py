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
    return {
        "APP_NAME": getattr(settings, "APP_NAME", "نظام العيادة"),
        "APP_VERSION": getattr(settings, "APP_VERSION", "1.0.0"),
        "FACILITY_NAME": getattr(settings, "FACILITY_NAME", "العيادة"),
        "LICENSE_STATE": trial,
    }
