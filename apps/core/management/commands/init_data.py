"""
أمر إدارة لإنشاء البيانات الأولية الضرورية:
- الأدوار الأربعة
- الأقسام الافتراضية
- إصدار البرنامج الحالي
- حالة الترخيص التجريبي
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "تهيئة البيانات الأولية للنظام (الأدوار، الأقسام، الإصدار، الترخيص)"

    def handle(self, *args, **options):
        self._create_roles()
        self._create_departments()
        self._create_app_version()
        self._create_license()
        self.stdout.write(self.style.SUCCESS("✅ تمت تهيئة البيانات الأولية بنجاح."))

    def _create_roles(self):
        from apps.accounts.models import Role
        roles = [
            {"code": "owner",       "name": "المالك",          "description": "مالك النظام - صلاحيات كاملة", "is_system_role": True},
            {"code": "doctor",      "name": "الطبيب",          "description": "طبيب العيادة"},
            {"code": "organizer",   "name": "المنظم",          "description": "منظم المرضى والمواعيد"},
            {"code": "data_auditor","name": "مدقق البيانات",   "description": "مدقق ومراجع البيانات"},
        ]
        for rd in roles:
            _, created = Role.objects.get_or_create(code=rd["code"], defaults=rd)
            if created:
                self.stdout.write(f"  + دور: {rd['name']}")

    def _create_departments(self):
        from apps.core.models import Department
        depts = [
            {"code": "GENERAL", "name": "العيادة العامة"},
            {"code": "LAB",     "name": "المختبر"},
            {"code": "EYE",     "name": "عيادة العيون"},
            {"code": "REF",     "name": "الإحالات"},
        ]
        for dd in depts:
            _, created = Department.objects.get_or_create(code=dd["code"], defaults=dd)
            if created:
                self.stdout.write(f"  + قسم: {dd['name']}")

    def _create_app_version(self):
        from apps.core.models import AppVersion
        ver, created = AppVersion.objects.get_or_create(
            version_number="1.0.0",
            defaults={
                "channel": "develop",
                "is_current": True,
                "release_date": timezone.now().date(),
                "db_schema_version": "1",
                "notes": "النسخة التجريبية الأولى - المرحلة 1",
            },
        )
        if created:
            self.stdout.write(f"  + إصدار: {ver.version_number}")

    def _create_license(self):
        from apps.core.models import LicenseState
        if LicenseState.objects.exists():
            return
        LicenseState.objects.create(
            activation_date=timezone.now(),
            trial_days=30,
            expires_at=timezone.now() + timedelta(days=30),
            is_trial=True,
            is_expired=False,
            mode="trial",
        )
        self.stdout.write("  + حالة الترخيص التجريبي (30 يوم)")
