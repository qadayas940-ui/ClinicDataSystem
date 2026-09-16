"""
أمر إدارة لإنشاء البيانات الأولية الضرورية:
- الأدوار الأربعة
- الأقسام الافتراضية
- إصدار البرنامج الحالي
"""
import hashlib
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "تهيئة البيانات الأولية للنظام (الأدوار، الأقسام، الإصدار)"

    def handle(self, *args, **options):
        self._create_roles()
        self._create_departments()
        self._create_app_version()
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
            version_number="1.1.0",
            defaults={
                "channel": "develop",
                "is_current": True,
                "release_date": timezone.now().date(),
                "db_schema_version": "1",
                "notes": "إصدار عيادة الموصل الخيرية للإنتاج",
            },
        )
        if created:
            self.stdout.write(f"  + إصدار: {ver.version_number}")

    def _create_server_settings(self):
        import os

        from apps.core.models import ServerSettings
        allow_lan = os.environ.get("CLINIC_ALLOW_LAN", "false").lower() in {"1", "true", "yes"}
        port = int(os.environ.get("CLINIC_PORT", "8765"))
        ServerSettings.objects.update_or_create(pk=1, defaults={
            "port": port,
            "allow_network_access": allow_lan,
            "bind_address": "0.0.0.0" if allow_lan else "127.0.0.1",
        })

    def _create_reference_catalog(self):
        from apps.core.models import Department, ReferenceValue

        catalog_path = Path(__file__).resolve().parents[2] / "excel_reference_catalog.json"
        if not catalog_path.exists():
            self.stdout.write(self.style.WARNING("لم يُعثر على قاموس Excel المضمّن."))
            return
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))
        department_by_name = {}
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
                department, _ = Department.all_objects.update_or_create(
                    code=code,
                    defaults={"name": item.canonical_name, "department_type": "clinic", "is_active": True, "deleted_at": None},
                )
                department_by_name[item.canonical_name] = department
        for entry in entries:
            if entry["category"] != "doctor":
                continue
            item = ReferenceValue.objects.get(category="doctor", normalized_name=entry["normalized_name"])
            item.departments.set([
                department_by_name[name]
                for name in entry.get("departments", [])
                if name in department_by_name
            ])
        department_names = {name.strip() for name in department_by_name}
        for item in ReferenceValue.objects.filter(category="doctor"):
            bare = re.sub(r"^(?:د\s*[./-]?|دكتور(?:ة)?)\s*", "", item.canonical_name).strip()
            if bare in department_names:
                item.is_active = False
                item.needs_review = True
                item.save(update_fields=["is_active", "needs_review", "updated_at"])
        self.stdout.write(f"  + القيم المرجعية المستخرجة من Excel: {len(entries)}")
