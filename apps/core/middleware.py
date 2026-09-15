"""
وسيط تسجيل التدقيق (Audit Log Middleware).

يسجّل العمليات المهمة (طلبات التعديل POST/PUT/PATCH/DELETE) دون تخزين
أي بيانات حساسة مثل كلمات المرور أو أرقام الهوية.
"""
import ipaddress
import logging

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone

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
        host = request.get_host().split(":", 1)[0].strip("[]").lower()
        if settings.DEBUG or host in {"localhost", "testserver"}:
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


class TrialReadOnlyMiddleware:
    """يبقي البيانات قابلة للقراءة والتصدير بعد انتهاء التجربة ويمنع تعديلها."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in self.SAFE_METHODS or self._is_exempt(request.path):
            return self.get_response(request)

        from .models import LicenseState

        state = LicenseState.objects.first()
        if state and state.expires_at and state.expires_at <= timezone.now() and state.mode != "licensed":
            if state.mode != "read_only" or not state.is_expired:
                LicenseState.objects.filter(pk=state.pk).update(mode="read_only", is_expired=True)
            if request.path.startswith("/api/"):
                return JsonResponse(
                    {"error": "trial_expired", "message": "انتهت التجربة؛ النظام متاح للقراءة والتصدير فقط."},
                    status=403,
                )
            messages.warning(request, "انتهت مدة التجربة. بقيت البيانات متاحة للقراءة والنسخ والتصدير بأمان.")
            return redirect("core:dashboard")
        return self.get_response(request)

    @staticmethod
    def _is_exempt(path):
        return any(path.startswith(prefix) for prefix in settings.CLINIC_READ_ONLY_EXEMPT_PATHS)
