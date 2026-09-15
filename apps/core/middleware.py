"""
وسيط تسجيل التدقيق (Audit Log Middleware).

يسجّل العمليات المهمة (طلبات التعديل POST/PUT/PATCH/DELETE) دون تخزين
أي بيانات حساسة مثل كلمات المرور أو أرقام الهوية.
"""
import logging

from .utils import get_client_ip

logger = logging.getLogger("clinic")

# المسارات التي لها معالجة تدقيق خاصة في العروض (نتجنب التكرار)
SKIP_PREFIXES = ("/static/", "/media/", "/api/health", "/accounts/login", "/accounts/logout")
AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditLogMiddleware:
    """
    يسجّل ملخصاً للعمليات المُعدِّلة للبيانات.

    يخزّن: المستخدم، الإجراء، المسار، عنوان IP، وكيل المتصفح — بدون محتوى الطلب.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            if request.method in AUDIT_METHODS and not request.path.startswith(SKIP_PREFIXES):
                user = getattr(request, "user", None)
                if user is not None and user.is_authenticated:
                    from .models import AuditLog

                    action = "delete" if request.method == "DELETE" else "update"
                    AuditLog.objects.create(
                        user=user,
                        action=action,
                        model_name="",
                        object_repr=request.path[:255],
                        # لا نخزّن جسم الطلب لتجنب البيانات الحساسة
                        changes={"method": request.method, "status": response.status_code},
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("تعذّر تسجيل التدقيق في الوسيط: %s", exc)

        return response
