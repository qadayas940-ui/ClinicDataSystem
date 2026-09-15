"""عروض النواة: فحص الصحة (Health Check)، الشاشة الرئيسية (Dashboard)."""
import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import BackupHistory, LicenseState

logger = logging.getLogger("clinic")
User = get_user_model()


def _get_db_size_mb():
    """حساب حجم ملف قاعدة بيانات SQLite بالميغابايت."""
    try:
        db_path = settings.DATABASES["default"]["NAME"]
        if db_path and db_path != ":memory:" and os.path.exists(db_path):
            return round(os.path.getsize(db_path) / (1024 * 1024), 2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("تعذّر حساب حجم قاعدة البيانات: %s", exc)
    return 0.0


def _check_db():
    """التحقق من الاتصال بقاعدة البيانات."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("فشل الاتصال بقاعدة البيانات: %s", exc)
        return False


def _get_trial_days_remaining():
    """أيام التجربة المتبقية من حالة الترخيص (إن وُجدت)."""
    license_state = LicenseState.objects.first()
    if license_state:
        return license_state.trial_days_remaining
    return getattr(settings, "DEFAULT_TRIAL_DAYS", 30)


def _collect_health():
    """تجميع بيانات صحة النظام."""
    db_ok = _check_db()
    try:
        users_count = User.objects.count()
    except Exception:  # noqa: BLE001
        users_count = 0
    return {
        "status": "ok" if db_ok else "error",
        "version": getattr(settings, "APP_VERSION", "1.0.0"),
        "db_status": "connected" if db_ok else "disconnected",
        "db_size_mb": _get_db_size_mb(),
        "trial_days_remaining": _get_trial_days_remaining(),
        "server_time": timezone.now().isoformat(),
        "users_count": users_count,
    }


def health_check(request):
    """
    نقطة فحص صحة النظام (GET /api/health/).

    تُعيد JSON يوضّح حالة النظام وقاعدة البيانات والإصدار وأيام التجربة.
    """
    data = _collect_health()
    http_status = 200 if data["status"] == "ok" else 503
    return JsonResponse(data, status=http_status, json_dumps_params={"ensure_ascii": False})


@login_required
def health_check_page(request):
    """شاشة فحص الصحة بواجهة عربية."""
    data = _collect_health()
    return render(request, "core/health_check.html", {"health": data})


@login_required
def dashboard(request):
    """الشاشة الرئيسية بعد تسجيل الدخول."""
    health = _collect_health()
    last_backup = BackupHistory.objects.filter(status="success").order_by("-created_at").first()
    context = {
        "health": health,
        "last_backup": last_backup,
        "server_running": True,
    }
    return render(request, "core/dashboard.html", context)
