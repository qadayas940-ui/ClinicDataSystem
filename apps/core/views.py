"""عروض النواة: فحص الصحة (Health Check)، الشاشة الرئيسية (Dashboard)."""
import json
import logging
import os
import socket

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import DepartmentForm, ServerSettingsForm
from .models import BackupHistory, Department, LicenseState, ServerSettings
from .utils import log_audit, owner_required

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
    if not request.user.is_authenticated:
        data = {"status": data["status"], "version": data["version"]}
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
    from apps.laboratory.models import LabOrder
    from apps.patients.models import Patient
    from apps.referrals.models import Referral
    from apps.visits.models import Visit

    today = timezone.localdate()
    context = {
        "health": health,
        "last_backup": last_backup,
        "server_running": True,
        "patient_count": Patient.objects.count(),
        "today_visits": Visit.objects.filter(visit_date__date=today).count(),
        "pending_labs": LabOrder.objects.filter(status="pending").count(),
        "pending_referrals": Referral.objects.filter(status="pending").count(),
    }
    return render(request, "core/dashboard.html", context)


@owner_required
def department_list(request):
    return render(request, "core/departments.html", {"departments": Department.objects.all()})


@owner_required
def department_form(request, pk=None):
    department = get_object_or_404(Department, pk=pk) if pk else None
    form = DepartmentForm(request.POST or None, instance=department)
    if request.method == "POST" and form.is_valid():
        department = form.save()
        log_audit(request, "update" if pk else "create", "Department", department.pk, department.name)
        return redirect("core:departments")
    return render(request, "shared/form.html", {"form": form, "title": "تعديل القسم" if pk else "إضافة قسم", "submit_label": "حفظ القسم"})


@owner_required
def department_archive(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        department.soft_delete()
        log_audit(request, "delete", "Department", department.pk, department.name)
    return redirect("core:departments")


def _local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


@owner_required
def server_settings(request):
    server, _ = ServerSettings.objects.get_or_create(pk=1)
    form = ServerSettingsForm(request.POST or None, instance=server)
    if request.method == "POST" and form.is_valid():
        server = form.save(commit=False)
        server.bind_address = "0.0.0.0" if server.allow_network_access else "127.0.0.1"
        server.save()
        try:
            import launcher_config

            launcher_config.CONFIG_HOME.mkdir(parents=True, exist_ok=True)
            payload = {"data_path": str(settings.DATA_PATH), "allow_lan": server.allow_network_access, "port": server.port}
            launcher_config.CONFIG_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except (ImportError, OSError) as exc:
            logger.warning("تعذر كتابة إعداد سطح المكتب: %s", exc)
        messages.success(request, "حُفظ الإعداد. أعد تشغيل التطبيق لتطبيق تغيير الشبكة أو المنفذ.")
        return redirect("core:server_settings")
    return render(request, "core/server_settings.html", {"form": form, "server": server, "lan_url": f"http://{_local_ip()}:{server.port}"})
