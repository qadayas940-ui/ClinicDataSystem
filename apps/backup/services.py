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
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from apps.core.models import BackupHistory


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stamp():
    return timezone.localtime().strftime("%Y%m%d-%H%M%S")


def _export_dir(kind):
    path = Path(settings.DATA_PATH) / "Files" / kind
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

    patients = Patient.objects.select_related("primary_name").prefetch_related(
        "contacts", "addresses", "visits__department", "visits__doctor_reference", "visits__organizer_reference"
    ).order_by("created_at", "pk")
    patient_rows = []
    sequence = 0
    for patient in patients:
        visits = list(patient.visits.order_by("visit_date", "pk"))
        if not visits:
            visits = [None]
        for visit in visits:
            sequence += 1
            patient_rows.append([
                sequence, patient.internal_code, patient.display_name, patient.get_gender_display(),
                patient.calculated_age, patient.addresses.values_list("text", flat=True).first() or "",
                patient.contacts.values_list("value", flat=True).first() or "",
                str(visit.department or "") if visit else "", visit.diagnosis if visit else "",
                str(visit.doctor_reference or visit.doctor or "") if visit else "",
                str(visit.organizer_reference or visit.organizer or "") if visit else "",
                timezone.localtime(visit.visit_date).strftime("%Y/%m/%d — %I:%M %p").lstrip("0") if visit else "", visit.notes if visit else "",
            ])

    lab_rows = []
    for order in LabOrder.objects.select_related("patient", "patient__primary_name").prefetch_related("tests"):
        tests = list(order.tests.all()) or [None]
        for test in tests:
            lab_rows.append([
                len(lab_rows) + 1, order.patient.internal_code, order.patient.display_name,
                order.patient.calculated_age, test.test_name if test else "",
            ])

    referral_rows = [
        [index, item.patient.internal_code, item.patient.display_name, item.destination_name]
        for index, item in enumerate(
            Referral.objects.select_related("patient", "patient__primary_name"), start=1
        )
    ]
    eye_rows = [
        [index, item.patient.internal_code, item.patient.display_name, item.patient.calculated_age,
         item.diagnosis, item.notes]
        for index, item in enumerate(
            EyeClinicVisit.objects.select_related("patient", "patient__primary_name"), start=1
        )
    ]
    return [
        ("المرضى", ["ت", "الرقم التعريفي الخاص بالمريض", "الاسم", "الجنس", "العمر", "العنوان",
                     "رقم الهاتف", "القسم", "الحالة", "اسم الطبيب", "اسم المنظم", "التاريخ", "الملاحظات"], patient_rows),
        ("المختبر", ["ت", "الرقم التعريفي", "الاسم", "العمر", "نوع الفحص"], lab_rows),
        ("الإحالات", ["ت", "الرقم التعريفي", "الاسم", "الطبيب المحال إليه"], referral_rows),
        ("عيادة العيون", ["ت", "الرقم التعريفي", "الاسم", "العمر", "التشخيص", "الملاحظات"], eye_rows),
    ]


def _plain(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _style_excel_sheet(sheet, table_name=None):
    sheet.sheet_view.rightToLeft = True
    sheet.freeze_panes = "A2"
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="087F73")
    if table_name and sheet.max_row >= 2:
        table = Table(displayName=table_name, ref=f"A1:{sheet.cell(1, sheet.max_column).column_letter}{sheet.max_row}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium4", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
        sheet.add_table(table)
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(45, max(12, max(len(str(cell.value or "")) for cell in column) + 2))


def _safe_sheet_title(value, existing):
    cleaned = "".join("_" if char in '[]:*?/\\\\' else char for char in str(value or "غير محدد")).strip()[:25]
    base = f"قسم - {cleaned or 'غير محدد'}"
    title, counter = base[:31], 2
    while title in existing:
        suffix = f"-{counter}"
        title = base[:31-len(suffix)] + suffix
        counter += 1
    return title


def create_excel_export():
    path = _export_dir("Excel") / f"ClinicData-export-{_stamp()}.xlsx"
    book = Workbook()
    book.remove(book.active)
    exported = _export_tables()
    for index, (title, headers, rows) in enumerate(exported, start=1):
        sheet = book.create_sheet(title=title)
        sheet.append(headers)
        for row in rows:
            sheet.append([_plain(value) for value in row])
        _style_excel_sheet(sheet, f"ClinicTable{index}")
    patient_headers, patient_rows = exported[0][1], exported[0][2]
    index_sheet = book.create_sheet("اختصاصات")
    index_sheet.append(["الاختصاص", "عدد السجلات", "اسم الورقة"])
    groups = {}
    for row in patient_rows:
        groups.setdefault(str(row[7] or "غير محدد"), []).append(row)
    existing = set(book.sheetnames)
    for number, (department, rows) in enumerate(sorted(groups.items()), start=1):
        title = _safe_sheet_title(department, existing)
        existing.add(title)
        specialty = book.create_sheet(title)
        specialty.append(patient_headers)
        for row in rows:
            specialty.append([_plain(value) for value in row])
        _style_excel_sheet(specialty, f"SpecialtyTable{number}")
        index_sheet.append([department, len(rows), title])
        index_sheet.cell(index_sheet.max_row, 3).hyperlink = f"#'{title}'!A1"
    _style_excel_sheet(index_sheet, "SpecialtiesIndex")
    search = book.create_sheet("البحث")
    search.sheet_view.rightToLeft = True
    search["A1"] = "البحث عن مريض"
    search["A1"].font = Font(bold=True, color="FFFFFF", size=16)
    search["A1"].fill = PatternFill("solid", fgColor="062F50")
    search.merge_cells("A1:F1")
    search["A3"], search["B3"] = "اختر الاسم", ""
    if patient_rows:
        validation = DataValidation(type="list", formula1=f"'المرضى'!$C$2:$C${len(patient_rows)+1}", allow_blank=True)
        search.add_data_validation(validation)
        validation.add(search["B3"])
    labels = [("A5","الرقم التعريفي","B5","B"),("C5","الجنس","D5","D"),("E5","العمر","F5","E"),("A7","العنوان","B7","F"),("C7","رقم الهاتف","D7","G"),("E7","القسم","F7","H"),("A9","الحالة","B9","I"),("C9","اسم الطبيب","D9","J"),("E9","التاريخ","F9","L")]
    for label_cell, label, value_cell, source_col in labels:
        search[label_cell] = label
        search[label_cell].font = Font(bold=True, color="062F50")
        search[value_cell] = f'=IFERROR(INDEX(المرضى!${source_col}:${source_col},MATCH($B$3,المرضى!$C:$C,0)),"")'
    search["A12"] = "جميع زيارات الاسم المختار (Excel 365)"
    search["A13"] = '=IF($B$3="","",_xlfn._xlws.FILTER(المرضى!A:M,المرضى!C:C=$B$3,"لا توجد زيارات"))'
    for column, width in {"A":22,"B":28,"C":18,"D":24,"E":18,"F":28}.items():
        search.column_dimensions[column].width = width
    changes = book.create_sheet("التغييرات")
    changes.append(["العملية","الرقم التعريفي","الاسم","القسم","التاريخ","الملاحظات"])
    changes.append(["","","","","","تُراجع عبر شاشة الاستيراد قبل الدمج؛ لا تُستبدل قاعدة البيانات مباشرة."])
    operation_validation = DataValidation(type="list", formula1='"إضافة,تعديل,أرشفة"', allow_blank=True)
    changes.add_data_validation(operation_validation)
    operation_validation.add("A2:A5000")
    _style_excel_sheet(changes, "ChangesTable")
    book.save(path)
    return path

def create_csv_export():
    path = _export_dir("ZIP") / f"ClinicData-export-{_stamp()}.zip"
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
    path = _export_dir("JSON") / f"ClinicData-export-{_stamp()}.json"
    payload = {}
    for title, headers, rows in _export_tables():
        payload[title] = [dict(zip(headers, [_plain(value) for value in row])) for row in rows]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
