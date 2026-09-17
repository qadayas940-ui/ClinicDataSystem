"""عروض النواة: فحص الصحة (Health Check)، الشاشة الرئيسية (Dashboard)."""
import json
import logging
import os
import re
import socket
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection, models
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import DepartmentForm, ReferenceValueForm, ServerSettingsForm
from .models import BackupHistory, Department, Notification, ReferenceValue, ServerSettings
from .utils import log_audit, owner_required, roles_required

logger = logging.getLogger("clinic")
User = get_user_model()


@login_required
def set_language(request, language):
    language = "en" if language == "en" else "ar"
    response = redirect(request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("core:dashboard"))
    response.set_cookie("django_language", language, max_age=365 * 24 * 60 * 60, samesite="Lax")
    return response


@login_required
def notifications(request):
    items = request.user.notifications.all()[:100]
    if request.method == "POST":
        request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "unread": 0})
        messages.success(request, "تم تعليم الإشعارات كمقروءة.")
        return redirect("core:notifications")
    return render(request, "core/notifications.html", {"notifications": items})


@login_required
def notification_open(request, pk):
    item = get_object_or_404(Notification, pk=pk, user=request.user)
    if item.read_at is None:
        item.read_at = timezone.now()
        item.save(update_fields=["read_at", "updated_at"])
    target = item.target_url or reverse("core:notifications")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = reverse("core:notifications")
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "target_url": target, "unread": request.user.notifications.filter(read_at__isnull=True).count()})
    return redirect(target)


@login_required
def notifications_status(request):
    unread = request.user.notifications.filter(read_at__isnull=True).count()
    latest = request.user.notifications.order_by("-created_at").values_list("created_at", flat=True).first()
    return JsonResponse({"unread": unread, "latest": latest.isoformat() if latest else ""})


def _get_db_size_mb():
    """حساب حجم قاعدة البيانات في SQLite أو PostgreSQL."""
    try:
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(current_database())")
                return round(cursor.fetchone()[0] / (1024 * 1024), 2)
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
        "database_engine": connection.vendor,
        "server_time": timezone.now().isoformat(),
        "users_count": users_count,
    }


def health_check(request):
    """
    نقطة فحص صحة النظام (GET /api/health/).

    تُعيد JSON يوضّح حالة النظام وقاعدة البيانات والإصدار.
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
    period = request.GET.get("period", "today")
    start = end = None
    if period == "today": start = end = today
    elif period == "week": start, end = today - timedelta(days=today.weekday()), today
    elif period == "month": start, end = today.replace(day=1), today
    elif period == "custom":
        start = parse_date(request.GET.get("start", ""))
        end = parse_date(request.GET.get("end", ""))
    patient_qs = Patient.objects.all()
    visit_qs = Visit.objects.all()
    lab_qs = LabOrder.objects.all()
    referral_qs = Referral.objects.all()
    if start: patient_qs = patient_qs.filter(created_at__date__gte=start); visit_qs = visit_qs.filter(visit_date__date__gte=start); lab_qs = lab_qs.filter(order_date__date__gte=start); referral_qs = referral_qs.filter(referral_date__date__gte=start)
    if end: patient_qs = patient_qs.filter(created_at__date__lte=end); visit_qs = visit_qs.filter(visit_date__date__lte=end); lab_qs = lab_qs.filter(order_date__date__lte=end); referral_qs = referral_qs.filter(referral_date__date__lte=end)
    context = {
        "health": health,
        "last_backup": last_backup,
        "server_running": True,
        "patient_count": patient_qs.count(),
        "today_visits": visit_qs.count(),
        "pending_labs": lab_qs.filter(status="pending").count(),
        "pending_referrals": referral_qs.filter(status="pending").count(),
        "department_count": Department.objects.filter(is_active=True).count(),
        "doctor_count": ReferenceValue.objects.filter(category="doctor", is_active=True).count(),
        "active_departments": Department.objects.filter(is_active=True).annotate(
            doctor_total=models.Count(
                "reference_values",
                filter=models.Q(reference_values__category="doctor", reference_values__is_active=True),
                distinct=True,
            )
        ).order_by("name"),
        "period": period, "start": start, "end": end,
        "visits_by_department": visit_qs.values("department__name").annotate(total=models.Count("id")).order_by("-total")[:8],
    }
    return render(request, "core/dashboard.html", context)


@owner_required
def department_list(request):
    return render(request, "core/departments.html", {"departments": Department.objects.all()})


@owner_required
def settings_home(request):
    reference_counts = {
        key: ReferenceValue.objects.filter(category=key, is_active=True).count()
        for key, _ in ReferenceValue.CATEGORY_CHOICES
    }
    return render(request, "core/settings.html", {"reference_counts": reference_counts})


@owner_required
def reference_list(request):
    category = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()
    items = ReferenceValue.objects.all()
    if category:
        items = items.filter(category=category)
    if query:
        items = items.filter(canonical_name__icontains=query)
    page = Paginator(items, 100).get_page(request.GET.get("page"))
    return render(request, "core/reference_list.html", {
        "page": page,
        "category": category,
        "query": query,
        "categories": ReferenceValue.CATEGORY_CHOICES,
    })


@owner_required
def reference_form(request, pk=None):
    item = get_object_or_404(ReferenceValue, pk=pk) if pk else None
    form = ReferenceValueForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.normalized_name = re.sub(r"\s+", " ", item.canonical_name.strip().lower())
        item.save()
        form.save_m2m()
        messages.success(request, "تم حفظ القيمة المرجعية.")
        return redirect("core:reference_list")
    return render(request, "shared/form.html", {
        "form": form,
        "title": "تعديل قيمة مرجعية" if pk else "إضافة قيمة مرجعية",
        "submit_label": "حفظ",
    })


@roles_required("doctor", "organizer", "data_auditor")
@require_POST
def reference_quick_create(request):
    """Create/reuse a reference item directly from an editable combo box."""
    allowed = {key for key, _label in ReferenceValue.CATEGORY_CHOICES}
    category = request.POST.get("category", "").strip()
    name = re.sub(r"\s+", " ", request.POST.get("name", "").strip())
    if category not in allowed or len(name) < 2 or len(name) > 255:
        return JsonResponse({"ok": False, "error": "القيمة أو التصنيف غير صالح."}, status=400)
    normalized = re.sub(r"[إأآٱ]", "ا", name.lower())
    normalized = re.sub(r"ى", "ي", normalized)
    normalized = re.sub(r"ة", "ه", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if category == "department":
        item = Department.objects.filter(name__iexact=name).first()
        created = item is None
        if item is None:
            item = Department.objects.create(name=name, code=f"DPT-{uuid.uuid4().hex[:8].upper()}", is_active=True)
        log_audit(request, "create" if created else "update", "Department", item.pk, item.name)
        return JsonResponse({"ok": True, "created": created, "item": {"id": item.pk, "text": item.name}})
    item, created = ReferenceValue.all_objects.get_or_create(
        category=category, normalized_name=normalized,
        defaults={"canonical_name": name, "aliases": [name], "is_active": True},
    )
    if item.deleted_at:
        item.restore()
    if not item.is_active:
        item.is_active = True
        item.save(update_fields=["is_active", "updated_at"])
    department_id = request.POST.get("department")
    if category == "doctor" and department_id:
        department = Department.objects.filter(pk=department_id, is_active=True).first()
        if department:
            item.departments.add(department)
    log_audit(request, "create" if created else "update", "ReferenceValue", item.pk, item.canonical_name)
    return JsonResponse({"ok": True, "created": created, "item": {"id": item.pk, "text": item.canonical_name}})


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
    candidates = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        candidates.append(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()
    try:
        candidates.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    for candidate in candidates:
        try:
            if candidate != "127.0.0.1" and __import__("ipaddress").ip_address(candidate).is_private:
                return candidate
        except ValueError:
            continue
    return "127.0.0.1"


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
            payload = dict(getattr(launcher_config, "DESKTOP_CONFIG", {}) or {})
            payload.update({
                "data_path": str(settings.DATA_PATH),
                "allow_lan": server.allow_network_access,
                "port": server.port,
            })
            launcher_config.CONFIG_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except (ImportError, OSError) as exc:
            logger.warning("تعذر كتابة إعداد سطح المكتب: %s", exc)
        messages.success(request, "حُفظ الإعداد. أعد تشغيل التطبيق لتطبيق تغيير الشبكة أو المنفذ.")
        return redirect("core:server_settings")
    return render(request, "core/server_settings.html", {"form": form, "server": server, "lan_url": f"http://{_local_ip()}:{server.port}"})
