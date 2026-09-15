"""عروض (Views) تطبيق الحسابات: تسجيل الدخول/الخروج، إعداد المالك، تغيير كلمة المرور."""
import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.utils import get_client_ip, log_audit, owner_required

from .forms import (
    ArabicLoginForm,
    ArabicPasswordChangeForm,
    OwnerSetupForm,
    StaffUserForm,
)
from .models import User

logger = logging.getLogger("clinic")


def _owner_exists():
    """هل يوجد حساب مالك مُفعّل في النظام؟"""
    return User.objects.filter(role__code="owner").exists()


@transaction.atomic
def setup_owner(request):
    """إعداد حساب المالك الأول (يظهر فقط إن لم يوجد مالك بعد)."""
    if _owner_exists():
        messages.info(request, "تم إعداد النظام مسبقاً. يرجى تسجيل الدخول.")
        return redirect("accounts:login")

    if request.method == "POST":
        form = OwnerSetupForm(request.POST)
        if form.is_valid():
            if User.objects.select_for_update().filter(role__code="owner").exists():
                messages.info(request, "أنشأ جهاز آخر حساب المالك بالفعل. يرجى تسجيل الدخول.")
                return redirect("accounts:login")
            user = form.save()
            log_audit(request, "create", model_name="User", object_id=str(user.pk), object_repr=user.username)
            messages.success(request, "تم إنشاء حساب المالك بنجاح. يمكنك الآن تسجيل الدخول.")
            return redirect("accounts:login")
    else:
        form = OwnerSetupForm()
    return render(request, "accounts/setup_owner.html", {"form": form})


def login_view(request):
    """صفحة تسجيل الدخول العربية مع دعم القفل."""
    if not _owner_exists():
        return redirect("accounts:setup_owner")

    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = ArabicLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            # فحص القفل المسبق لعرض رسالة واضحة
            try:
                candidate = User.objects.get(username=username)
                if candidate.is_locked:
                    remaining = int((candidate.locked_until - timezone.now()).total_seconds() // 60) + 1
                    messages.error(request, f"الحساب مقفل مؤقتاً بسبب محاولات دخول فاشلة. حاول بعد {remaining} دقيقة.")
                    return render(request, "accounts/login.html", {"form": form})
            except User.DoesNotExist:
                candidate = None

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                user.last_login_ip = get_client_ip(request)
                user.save(update_fields=["last_login_ip"])
                log_audit(request, "login", model_name="User", object_id=str(user.pk), object_repr=user.username)
                if user.is_force_password_change:
                    messages.warning(request, "يجب تغيير كلمة المرور المؤقتة قبل المتابعة.")
                    return redirect("accounts:change_password")
                return redirect("core:dashboard")
            else:
                log_audit(request, "login_failed", model_name="User", object_repr=username)
                if candidate and candidate.is_locked:
                    messages.error(request, "تم قفل الحساب مؤقتاً بسبب تكرار المحاولات الفاشلة. حاول لاحقاً.")
                else:
                    messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
    else:
        form = ArabicLoginForm()
    return render(request, "accounts/login.html", {"form": form})


@login_required
@require_POST
def logout_view(request):
    """تسجيل الخروج."""
    log_audit(request, "logout", model_name="User", object_id=str(request.user.pk), object_repr=request.user.username)
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح.")
    return redirect("accounts:login")


@login_required
def change_password(request):
    """تغيير كلمة المرور (يُستخدم أيضاً لإجبار تغيير كلمة المرور المؤقتة)."""
    if request.method == "POST":
        form = ArabicPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.is_force_password_change = False
            user.save(update_fields=["is_force_password_change"])
            update_session_auth_hash(request, user)  # إبقاء الجلسة نشطة
            log_audit(request, "update", model_name="User", object_id=str(user.pk), object_repr="password_change")
            messages.success(request, "تم تغيير كلمة المرور بنجاح.")
            return redirect("core:dashboard")
    else:
        form = ArabicPasswordChangeForm(request.user)
    return render(request, "accounts/change_password.html", {"form": form})


@owner_required
def user_list(request):
    users = User.objects.select_related("role", "department").order_by("-is_active", "username")
    return render(request, "accounts/user_list.html", {"users": users})


@owner_required
def user_create(request):
    form = StaffUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.created_by = request.user
        user.save()
        log_audit(request, "create", "User", user.pk, user.username)
        messages.success(request, "تم إنشاء حساب الموظف. سيُطلب منه تغيير كلمة المرور عند أول دخول.")
        return redirect("accounts:user_list")
    return render(request, "shared/form.html", {"form": form, "title": "إنشاء حساب موظف", "submit_label": "إنشاء الحساب"})


@owner_required
def user_edit(request, pk):
    from django.shortcuts import get_object_or_404

    user = get_object_or_404(User, pk=pk)
    if user.is_owner:
        messages.error(request, "حساب المالك يُدار من إعدادات المالك وتغيير كلمة المرور فقط.")
        return redirect("accounts:user_list")
    form = StaffUserForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_audit(request, "update", "User", user.pk, user.username)
        messages.success(request, "تم تحديث الحساب.")
        return redirect("accounts:user_list")
    return render(request, "shared/form.html", {"form": form, "title": f"تعديل حساب {user.username}", "submit_label": "حفظ"})
