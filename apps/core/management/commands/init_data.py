"""
أمر إدارة لإنشاء البيانات الأولية الضرورية:
- الأدوار الأربعة
- الأقسام الافتراضية
- إصدار البرنامج الحالي
- حالة الترخيص التجريبي
"""
import hashlib
import json
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "تهيئة البيانات الأولية للنظام (الأدوار، الأقسام، الإصدار، الترخيص)"

    def handle(self, *args, **options):
        self._create_roles()
        self._create_departments()
        self._create_app_version()
        self._create_license()
        self._create_server_settings()
        self._create_reference_catalog()
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
            {"code": "GENERAL", "name": "العيادة العامة", "department_type": "clinic"},
            {"code": "LAB",     "name": "المختبر", "department_type": "laboratory"},
            {"code": "REF",     "name": "الإحالات", "department_type": "administration"},
        ]
        for dd in depts:
            _, created = Department.objects.get_or_create(code=dd["code"], defaults=dd)
            if created:
                self.stdout.write(f"  + قسم: {dd['name']}")
        Department.all_objects.filter(code="EYE").update(is_active=False, deleted_at=timezone.now())

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

    def _create_server_settings(self):
        from apps.core.models import ServerSettings
        ServerSettings.objects.get_or_create(pk=1, defaults={"port": 8765, "allow_network_access": False, "bind_address": "127.0.0.1"})

    def _create_reference_catalog(self):
        from apps.core.models import Department, ReferenceValue

        catalog_path = Path(__file__).resolve().parents[2] / "excel_reference_catalog.json"
        if not catalog_path.exists():
            self.stdout.write(self.style.WARNING("لم يُعثر على قاموس Excel المضمّن."))
            return
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))
        for entry in entries:
            item, _ = ReferenceValue.all_objects.update_or_create(
                category=entry["category"],
                normalized_name=entry["normalized_name"],
                defaults={
                    "canonical_name": entry["canonical_name"],
                    "aliases": entry["aliases"],
                    "source_sheets": entry["source_sheets"],
                    "occurrence_count": entry["occurrence_count"],
                    "needs_review": entry["needs_review"],
                    "deleted_at": None,
                },
            )
            if entry["category"] == "department":
                code = "XLS-" + hashlib.sha1(entry["normalized_name"].encode("utf-8")).hexdigest()[:8].upper()
                Department.all_objects.update_or_create(
                    code=code,
                    defaults={"name": item.canonical_name, "department_type": "clinic", "is_active": True, "deleted_at": None},
                )
        self.stdout.write(f"  + القيم المرجعية المستخرجة من Excel: {len(entries)}")
