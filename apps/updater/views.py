from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.core.utils import log_audit, owner_required

from .models import UpdateManifest
from .services import check_remote_manifest


@login_required
def update_list(request):
    return render(request, "updater/list.html", {"latest": UpdateManifest.objects.first(), "current_version": settings.APP_VERSION, "configured": bool(settings.UPDATE_MANIFEST_URL)})


@owner_required
def update_check(request):
    if request.method == "POST":
        try:
            item = check_remote_manifest()
            log_audit(request, "other", "UpdateManifest", item.pk, item.version)
            messages.success(request, f"تم فحص قناة التحديث. أحدث إصدار منشور: {item.version}.")
        except (OSError, ValueError) as exc:
            messages.warning(request, f"تعذّر فحص التحديث: {exc}")
    return redirect("updater:list")
