import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.utils import timezone
from openpyxl import Workbook

from apps.core.models import BackupHistory


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stamp():
    return timezone.localtime().strftime("%Y%m%d-%H%M%S")


def _export_dir():
    path = Path(settings.DATA_PATH) / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _database_snapshot(destination):
    """Create a consistent snapshot for SQLite or PostgreSQL without fixed paths."""
    database = settings.DATABASES["default"]
    vendor = connection.vendor
    connection.close()
    if vendor == "sqlite":
        output = destination / "clinic.db"
        source = sqlite3.connect(database["NAME"])
        target = sqlite3.connect(output)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return output, "sqlite"

    if vendor == "postgresql" and shutil.which("pg_dump"):
        output = destination / "clinic-postgresql.dump"
        command = ["pg_dump", "--format=custom", "--file", str(output)]
        for option, flag in (("HOST", "--host"), ("PORT", "--port"), ("USER", "--username")):
            if database.get(option):
                command.extend([flag, str(database[option])])
        command.append(str(database["NAME"]))
        environment = None
        if database.get("PASSWORD"):
            import os
            environment = os.environ.copy()
            environment["PGPASSWORD"] = str(database["PASSWORD"])
        subprocess.run(command, check=True, timeout=1800, env=environment, capture_output=True)
        return output, "postgresql-custom"

    output = destination / "clinic-data.json"
    call_command(
        "dumpdata", "--all", "--natural-foreign", "--natural-primary",
        "--exclude", "contenttypes", "--exclude", "auth.permission",
        output=str(output), verbosity=0,
    )
    return output, f"{vendor}-django-json"


def create_database_backup(user=None, backup_type="manual"):
    backup_dir = Path(settings.DATA_PATH) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    final_path = backup_dir / f"ClinicData-{_stamp()}.clinicbackup"
    history = BackupHistory.objects.create(
        backup_type=backup_type, status="in_progress", created_by=user,
        app_version=settings.APP_VERSION, db_version=settings.DB_SCHEMA_VERSION,
    )
    try:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            db_copy, database_format = _database_snapshot(temporary_path)
            manifest = {
                "format": "ClinicDataBackup/2", "created_at": timezone.now().isoformat(),
                "app_version": settings.APP_VERSION, "db_schema_version": settings.DB_SCHEMA_VERSION,
                "database_engine": connection.vendor, "database_format": database_format,
                "database_file": db_copy.name, "database_sha256": sha256_file(db_copy),
            }
            manifest_path = temporary_path / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            with zipfile.ZipFile(final_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                archive.write(db_copy, db_copy.name)
                archive.write(manifest_path, "manifest.json")
        history.file_path = str(final_path)
        history.file_size = final_path.stat().st_size
        history.checksum = sha256_file(final_path)
        history.status = "success"
        history.save()
        return history
    except Exception as exc:
        history.status = "failed"
        history.notes = str(exc)[:1000]
        history.save(update_fields=["status", "notes"])
        raise


def _export_tables():
    from apps.laboratory.models import LabOrder
    from apps.ophthalmology.models import EyeClinicVisit
    from apps.patients.models import Patient
    from apps.referrals.models import Referral
    from apps.visits.models import Visit

    patients = Patient.objects.select_related("primary_name").prefetch_related("contacts", "addresses", "visits")
    visits = Visit.objects.select_related("patient", "department", "doctor", "doctor_reference", "organizer", "organizer_reference")
    return [
        ("المرضى", ["الرقم", "الاسم", "الجنس", "تاريخ الميلاد", "العمر", "الهاتف", "العنوان", "المصدر", "المعرف الخارجي", "عدد المراجعات"],
         ([p.internal_code, p.display_name, p.get_gender_display(), p.date_of_birth, p.calculated_age,
           p.contacts.values_list("value", flat=True).first() or "", p.addresses.values_list("text", flat=True).first() or "",
           p.source_type, p.external_id, p.total_visit_count] for p in patients)),
        ("مراجعة المرضى", ["الرقم", "المريض", "التاريخ", "نوع الزيارة", "القسم", "الطبيب", "المنظم", "الحالة", "الشكوى", "التشخيص", "الملاحظات", "المصدر"],
         ([v.pk, v.patient.internal_code, v.visit_date.isoformat(), v.get_visit_type_display(), str(v.department or ""),
           str(v.doctor_reference or v.doctor or ""), str(v.organizer_reference or v.organizer or ""),
           v.get_status_display(), v.chief_complaint, v.diagnosis, v.notes, v.source] for v in visits)),
        ("المختبر", ["الرقم", "المريض", "التاريخ", "الحالة", "الملاحظات"],
         ([o.pk, o.patient.internal_code, o.order_date.isoformat(), o.get_status_display(), o.notes]
          for o in LabOrder.objects.select_related("patient"))),
        ("الإحالات", ["الرقم", "المريض", "التاريخ", "الجهة", "السبب", "الحالة"],
         ([r.pk, r.patient.internal_code, r.referral_date.isoformat(), r.destination_name, r.reason, r.get_status_display()]
          for r in Referral.objects.select_related("patient"))),
        ("عيادة العيون", ["الرقم", "المريض", "التاريخ", "حدة يمين", "حدة يسار", "ضغط يمين", "ضغط يسار", "التشخيص"],
         ([e.pk, e.patient.internal_code, e.visit_date.isoformat(), e.visual_acuity_right, e.visual_acuity_left,
           e.iop_right, e.iop_left, e.diagnosis] for e in EyeClinicVisit.objects.select_related("patient"))),
    ]


def _plain(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def create_excel_export():
    path = _export_dir() / f"ClinicData-export-{_stamp()}.xlsx"
    book = Workbook(write_only=True)
    for title, headers, rows in _export_tables():
        sheet = book.create_sheet(title=title)
        sheet.append(headers)
        for row in rows:
            sheet.append([_plain(value) for value in row])
    book.save(path)
    return path


def create_csv_export():
    path = _export_dir() / f"ClinicData-export-{_stamp()}.zip"
    with tempfile.TemporaryDirectory() as temporary:
        temporary_path = Path(temporary)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for title, headers, rows in _export_tables():
                csv_path = temporary_path / f"{title}.csv"
                with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(headers)
                    writer.writerows([_plain(value) for value in row] for row in rows)
                archive.write(csv_path, csv_path.name)
    return path


def create_json_export():
    path = _export_dir() / f"ClinicData-export-{_stamp()}.json"
    payload = {}
    for title, headers, rows in _export_tables():
        payload[title] = [dict(zip(headers, [_plain(value) for value in row])) for row in rows]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
