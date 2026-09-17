"""
وسيط تسجيل التدقيق (Audit Log Middleware).

يسجّل العمليات المهمة (طلبات التعديل POST/PUT/PATCH/DELETE) دون تخزين
أي بيانات حساسة مثل كلمات المرور أو أرقام الهوية.
"""
import ipaddress
import logging

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.http.request import split_domain_port

from .utils import get_client_ip

logger = logging.getLogger("clinic")

# المسارات التي لها معالجة تدقيق خاصة في العروض (نتجنب التكرار)
SKIP_PREFIXES = ("/static/", "/media/", "/api/health", "/accounts/login", "/accounts/logout")
AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class PrivateNetworkHostMiddleware:
    """يسمح بالوصول المحلي وعناوين الشبكة الخاصة ويمنع DNS rebinding."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # لا نستخدم request.get_host() هنا؛ لأنه يتحقق من ALLOWED_HOSTS قبل
        # أن نحصل على فرصة السماح بعناوين LAN الخاصة، فينتج Bad Request 400.
        raw_host = request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME", "")
        host, _port = split_domain_port(raw_host.lower())
        host = host.strip("[]").rstrip(".")
        if not host:
            return HttpResponseBadRequest("عنوان المضيف غير صالح.")
        configured_hosts = {item.lower() for item in settings.ALLOWED_HOSTS if item != "*"}
        if settings.DEBUG or host in {"localhost", "testserver"} or host in configured_hosts:
            return self.get_response(request)
        try:
            address = ipaddress.ip_address(host)
            if address.is_loopback or address.is_private:
                return self.get_response(request)
        except ValueError:
            pass
        return HttpResponseBadRequest("عنوان المضيف غير مسموح.")


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
