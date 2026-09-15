"""معالجات السياق (Context Processors) لإتاحة معلومات التطبيق في القوالب."""
from django.conf import settings


def app_info(request):
    """يوفّر اسم التطبيق وإصداره واسم المنشأة لكل القوالب."""
    return {
        "APP_NAME": getattr(settings, "APP_NAME", "نظام العيادة"),
        "APP_VERSION": getattr(settings, "APP_VERSION", "1.0.0"),
        "FACILITY_NAME": getattr(settings, "FACILITY_NAME", "العيادة"),
    }
