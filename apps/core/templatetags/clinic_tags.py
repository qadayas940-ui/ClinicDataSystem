"""وسوم قوالب مخصصة لنظام العيادة."""
from django import template

register = template.Library()


@register.filter(name="arabic_bool")
def arabic_bool(value):
    """تحويل القيمة المنطقية إلى نص عربي (نعم/لا)."""
    return "نعم" if value else "لا"


@register.filter(name="filesizeformat_mb")
def filesizeformat_mb(value):
    """تنسيق حجم بالبايت إلى ميغابايت بمنزلتين عشريتين."""
    try:
        return f"{float(value) / (1024 * 1024):.2f} م.ب"
    except (TypeError, ValueError):
        return "0.00 م.ب"


@register.simple_tag
def status_badge(status):
    """إرجاع صنف Bootstrap مناسب لحالة نصية."""
    mapping = {
        "ok": "success",
        "connected": "success",
        "success": "success",
        "warning": "warning",
        "error": "danger",
        "failed": "danger",
        "pending": "secondary",
    }
    return mapping.get(str(status).lower(), "secondary")
