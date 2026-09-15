import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone
from openpyxl import Workbook

from apps.core.models import BackupHistory


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def create_database_backup(user=None, backup_type="manual"):
    backup_dir = Path(settings.DATA_PATH) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    final_path = backup_dir / f"ClinicData-{stamp}.clinicbackup"
    history = BackupHistory.objects.create(backup_type=backup_type, status="in_progress", created_by=user, app_version=settings.APP_VERSION, db_version=settings.DB_SCHEMA_VERSION)
    try:
        with tempfile.TemporaryDirectory() as temporary:
            db_copy = Path(temporary) / "clinic.db"
            connection.close()
            source = sqlite3.connect(settings.DATABASES["default"]["NAME"])
            destination = sqlite3.connect(db_copy)
            try:
                source.backup(destination)
            finally:
                destination.close(); source.close()
            manifest = {"format": "ClinicDataBackup/1", "created_at": timezone.now().isoformat(), "app_version": settings.APP_VERSION, "db_schema_version": settings.DB_SCHEMA_VERSION, "database_sha256": sha256_file(db_copy)}
            manifest_path = Path(temporary) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            with zipfile.ZipFile(final_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                archive.write(db_copy, "clinic.db"); archive.write(manifest_path, "manifest.json")
        history.file_path = str(final_path); history.file_size = final_path.stat().st_size
        history.checksum = sha256_file(final_path); history.status = "success"; history.save()
        return history
    except Exception as exc:
        history.status = "failed"; history.notes = str(exc)[:1000]; history.save(update_fields=["status", "notes"])
        raise


def create_excel_export():
    from apps.laboratory.models import LabOrder
    from apps.ophthalmology.models import EyeClinicVisit
    from apps.patients.models import Patient
    from apps.referrals.models import Referral
    from apps.visits.models import Visit

    export_dir = Path(settings.DATA_PATH) / "exports"; export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"ClinicData-export-{timezone.localtime().strftime('%Y%m%d-%H%M%S')}.xlsx"
    book = Workbook(write_only=True)
    sheets = [
        ("المرضى", ["الرقم", "الاسم", "الجنس", "تاريخ الميلاد", "العمر", "الهاتف", "العنوان"], ([p.internal_code, p.display_name, p.get_gender_display(), p.date_of_birth, p.calculated_age, p.contacts.values_list("value", flat=True).first() or "", p.addresses.values_list("text", flat=True).first() or ""] for p in Patient.objects.select_related("primary_name").prefetch_related("contacts", "addresses"))),
        ("مراجعة المرضى", ["الرقم", "المريض", "التاريخ", "القسم", "الطبيب", "الحالة", "التشخيص", "الملاحظات"], ([v.pk, v.patient.internal_code, v.visit_date.isoformat(), str(v.department or ""), str(v.doctor or ""), v.get_status_display(), v.diagnosis, v.notes] for v in Visit.objects.select_related("patient", "department", "doctor"))),
        ("المختبر", ["الرقم", "المريض", "التاريخ", "الحالة", "الملاحظات"], ([o.pk, o.patient.internal_code, o.order_date.isoformat(), o.get_status_display(), o.notes] for o in LabOrder.objects.select_related("patient"))),
        ("الإحالات", ["الرقم", "المريض", "التاريخ", "الجهة", "السبب", "الحالة"], ([r.pk, r.patient.internal_code, r.referral_date.isoformat(), r.destination_name, r.reason, r.get_status_display()] for r in Referral.objects.select_related("patient"))),
        ("عيادة العيون", ["الرقم", "المريض", "التاريخ", "حدة يمين", "حدة يسار", "ضغط يمين", "ضغط يسار", "التشخيص"], ([e.pk, e.patient.internal_code, e.visit_date.isoformat(), e.visual_acuity_right, e.visual_acuity_left, e.iop_right, e.iop_left, e.diagnosis] for e in EyeClinicVisit.objects.select_related("patient"))),
    ]
    for title, headers, rows in sheets:
        ws = book.create_sheet(title=title); ws.append(headers)
        for row in rows: ws.append(row)
    book.save(path)
    return path
