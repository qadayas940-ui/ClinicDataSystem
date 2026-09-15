import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings

from .models import UpdateManifest


def check_remote_manifest():
    url = settings.UPDATE_MANIFEST_URL
    if not url:
        raise ValueError("لم يُضبط رابط بيان التحديث الرسمي بعد.")
    if urlparse(url).scheme != "https":
        raise ValueError("يجب أن يستخدم رابط التحديث HTTPS.")
    request = Request(url, headers={"User-Agent": f"ClinicDataSystem/{settings.APP_VERSION}"})
    with urlopen(request, timeout=12) as response:
        payload = json.loads(response.read(256 * 1024).decode("utf-8"))
    required = {"version", "download_url", "sha256"}
    if not required.issubset(payload) or len(payload["sha256"]) != 64:
        raise ValueError("بيان التحديث غير مكتمل أو غير صالح.")
    if urlparse(payload["download_url"]).scheme != "https":
        raise ValueError("رابط المثبت في البيان غير آمن.")
    return UpdateManifest.objects.create(
        version=payload["version"], channel=payload.get("channel", "stable"),
        update_type=payload.get("update_type", "optional"), download_url=payload["download_url"],
        sha256=payload["sha256"], min_supported_version=payload.get("min_supported_version", ""),
        message_ar=payload.get("message_ar", ""), is_mandatory=bool(payload.get("is_mandatory", False)),
        allow_postpone=bool(payload.get("allow_postpone", True)), grace_period_days=int(payload.get("grace_period_days", 0)),
    )
