"""أدوات مساعدة مشتركة للنواة."""
import logging

logger = logging.getLogger("clinic")

# حقول حساسة يجب عدم تسجيلها أبداً
SENSITIVE_FIELDS = {"password", "password1", "password2", "old_password",
                    "new_password1", "new_password2", "national_id", "license_key",
                    "csrfmiddlewaretoken"}


def get_client_ip(request):
    """استخراج عنوان IP للعميل من الطلب."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def scrub_sensitive(data):
    """إزالة الحقول الحساسة من قاموس قبل تسجيله."""
    if not isinstance(data, dict):
        return data
    return {k: ("***" if k.lower() in SENSITIVE_FIELDS else v) for k, v in data.items()}


def log_audit(request, action, model_name="", object_id="", object_repr="", changes=None):
    """
    تسجيل عملية في سجل التدقيق دون أي بيانات حساسة.

    يُستدعى من العروض عند الأحداث المهمة (دخول/خروج/إنشاء/تعديل/حذف).
    """
    # استيراد مؤجل لتجنب الاستيراد الدائري
    from .models import AuditLog

    user = getattr(request, "user", None)
    if user is not None and not user.is_authenticated:
        user = None

    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else "",
            object_repr=object_repr[:255] if object_repr else "",
            changes=scrub_sensitive(changes) if changes else None,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
    except Exception as exc:  # noqa: BLE001
        # لا نُفشل الطلب بسبب فشل التسجيل
        logger.warning("تعذّر كتابة سجل التدقيق: %s", exc)
