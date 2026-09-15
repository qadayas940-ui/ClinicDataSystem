"""
سكريبت إعداد قاعدة البيانات والبيانات الأولية.

الاستخدام:
    python scripts/init_db.py

يقوم بـ:
1. تطبيق ترحيلات Django (ينشئ قاعدة البيانات إن لم تكن موجودة)
2. إنشاء البيانات الأولية (أدوار، أقسام، إصدار، ترخيص)
3. التحقق من وجود حساب مالك وإرشاد المستخدم لإنشائه
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.accounts.models import Role

User = get_user_model()


def main():
    print("=" * 50)
    print("  نظام إدارة بيانات العيادة - الإعداد الأولي")
    print("=" * 50)

    # 1. تطبيق الترحيلات
    print("\n[1/3] تطبيق ترحيلات قاعدة البيانات...")
    call_command("migrate", interactive=False, verbosity=0)
    print("      ✅ تمت")

    # 2. إنشاء البيانات الأولية
    print("\n[2/3] تهيئة البيانات الأولية...")
    call_command("init_data")

    # 3. التحقق من المالك
    print("\n[3/3] التحقق من حساب المالك...")
    if User.objects.filter(role__code=Role.CODE_OWNER).exists():
        owner = User.objects.filter(role__code=Role.CODE_OWNER).first()
        print(f"      ✅ يوجد حساب مالك: {owner.username}")
    else:
        print("      ⚠️  لا يوجد حساب مالك بعد.")
        print("      افتح المتصفح على: http://127.0.0.1:8765/accounts/setup-owner/")
        print("      أو نفذ: python manage.py createsuperuser")

    print("\n" + "=" * 50)
    print("  النظام جاهز للتشغيل!")
    print("  شغّل: python launcher.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
