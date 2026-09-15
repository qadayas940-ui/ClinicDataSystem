"""
سكربت إعداد قاعدة البيانات.

- يضبط مسار البيانات ومتغيرات البيئة.
- يطبّق ترحيلات Django (ينشئ قاعدة البيانات إن لم تكن موجودة).
- يتحقق من وجود حساب مالك، وإن لم يوجد يوجّه المستخدم لإنشائه عبر الواجهة
  أو تفاعلياً عبر سطر الأوامر.
"""
import os
import sys
from pathlib import Path

# إضافة جذر المشروع إلى المسار
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402

from apps.accounts.models import Role  # noqa: E402

User = get_user_model()


def apply_migrations():
    """تطبيق الترحيلات لإنشاء/تحديث قاعدة البيانات."""
    print("جارٍ تطبيق ترحيلات قاعدة البيانات…")
    call_command("makemigrations", interactive=False, verbosity=1)
    call_command("migrate", interactive=False, verbosity=1)
    print("تم تجهيز قاعدة البيانات بنجاح.")


def ensure_owner():
    """التحقق من وجود مالك وإرشاد المستخدم لإنشائه إن لزم."""
    if User.objects.filter(role__code=Role.CODE_OWNER).exists():
        print("يوجد حساب مالك مسبقاً. النظام جاهز.")
        return
    print("\n=== لا يوجد حساب مالك بعد ===")
    print("لإنشاء حساب المالك الأول، شغّل التطبيق وافتح صفحة إعداد المالك:")
    print("  /accounts/setup-owner/")
    print("أو استخدم: python manage.py createsuperuser")


if __name__ == "__main__":
    apply_migrations()
    ensure_owner()
