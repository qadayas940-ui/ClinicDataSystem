import hashlib
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook

from .models import (
    DataIssue,
    ImportBatch,
    ImportFile,
    ImportSheet,
    MatchCandidate,
    SourceRow,
)

HEADER_ALIASES = {
    "sequence": {"ت", "تسلسل", "الرقم", "رقم", "م"},
    "name": {"الاسم", "اسم المريض", "اسم المراجع", "الاسم الرباعي"},
    "gender": {"الجنس", "النوع"},
    "age": {"العمر", "عمر"},
    "birth_date": {"تاريخ الميلاد", "تاريخ الولادة", "المواليد"},
    "phone": {"رقم الهاتف", "الهاتف", "الموبايل", "رقم الموبايل"},
    "address": {"العنوان", "منطقة السكن", "السكن", "المنطقة"},
    "department": {"القسم", "اسم القسم"},
    "doctor": {"اسم الطبيب", "الطبيب", "دكتور"},
    "organizer": {"اسم المنظم", "المنظم"},
    "date": {"التاريخ", "تاريخ الزيارة", "تاريخ الاحالة", "تاريخ الإحالة"},
    "status": {"الحالة", "حالة المريض"},
    "notes": {"الملاحظات", "ملاحظات"},
    "repeat_count": {"عدد التكرار", "التكرار"},
    "destination": {"جهة الاحالة", "جهة الإحالة", "الجهة المحال اليها", "الجهة المحال إليها"},
    "test": {"الفحص", "اسم الفحص", "التحليل"},
    "result": {"النتيجة", "نتيجة الفحص"},
    "diagnosis": {"التشخيص", "المرض"},
}
GENDERS = {"ذكر": "male", "ذ": "male", "male": "male", "m": "male", "انثى": "female", "أنثى": "female", "ا": "female", "female": "female", "f": "female"}
SHEET_PROFILES = {
    "مراجعه المرضي": [
        ("ت", "sequence"), ("الاسم", "name"), ("الجنس", "gender"), ("العمر", "age"),
        ("العنوان", "address"), ("رقم الهاتف", "phone"), ("عدد التكرار", "repeat_count"),
        ("القسم", "department"), ("الحالة", "status"), ("اسم الطبيب", "doctor"),
        ("اسم المنظم", "organizer"), ("التاريخ", "date"), ("الملاحظات", "notes"),
    ],
    "المختبر": [("ت", "sequence"), ("الاسم", "name"), ("العمر", "age"), ("نوع الفحص", "test"), ("الملاحظات", "notes")],
    "احالات": [("ت", "sequence"), ("الاسم", "name"), ("الطبيب", "doctor")],
    "الاحالات": [("ت", "sequence"), ("الاسم", "name"), ("الطبيب", "doctor")],
    "عياده العيون": [("ت", "sequence"), ("الاسم", "name"), ("العمر", "age"), ("الجنس", "gender"), ("المنطقه", "address")],
}


def _text(value):
    return "" if value is None else re.sub(r"\s+", " ", str(value)).strip()


def normalize_arabic(value):
    value = _text(value).lower()
    return value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}))


def _canonical_header(value):
    normalized = normalize_arabic(value)
    for key, aliases in HEADER_ALIASES.items():
        if normalized in {normalize_arabic(alias) for alias in aliases}:
            return key
    return ""


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_upload(uploaded_file):
    incoming = Path(settings.UPLOADS_DIR) / "imports" / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    temp_path = incoming / f"upload-{timezone.now().strftime('%Y%m%d%H%M%S%f')}.xlsx"
    with temp_path.open("wb") as output:
        for chunk in uploaded_file.chunks(): output.write(chunk)
    digest = _file_hash(temp_path)
    archive = Path(settings.UPLOADS_DIR) / "imports" / digest[:2]
    archive.mkdir(parents=True, exist_ok=True)
    final_path = archive / f"{digest}.xlsx"
    if final_path.exists():
        temp_path.unlink()
    else:
        shutil.move(str(temp_path), final_path)
    return final_path, digest


def _detect_header(ws):
    best_row, best_score = 1, -1
    for row_index, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 25), values_only=True), 1):
        nonempty = [_text(value) for value in row if _text(value)]
        known = sum(bool(_canonical_header(value)) for value in nonempty)
        score = known * 5 + min(len(nonempty), 20)
        if score > best_score:
            best_row, best_score = row_index, score
    return best_row


def _headers(ws, header_row):
    values = next(ws.iter_rows(min_row=header_row, max_row=header_row, values_only=True))
    headers, seen = [], {}
    for index, value in enumerate(values, 1):
        name = _text(value) or f"عمود_{index}"
        seen[name] = seen.get(name, 0) + 1
        headers.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    while headers and headers[-1].startswith("عمود_"):
        headers.pop()
    return headers


def _validate(canonical, raw):
    issues, reasons = [], []
    name = _text(canonical.get("name"))
    if not name:
        issues.append(("name", "blocking", "اسم المريض مفقود", ""))
    gender_raw = normalize_arabic(canonical.get("gender"))
    age_raw = _text(canonical.get("age"))
    if gender_raw and gender_raw not in {normalize_arabic(k) for k in GENDERS}:
        issues.append(("gender", "warning", "قيمة الجنس غير معتمدة", "ذكر / أنثى / غير محدد"))
    if age_raw:
        try:
            age = float(age_raw)
            if age < 0 or age > 130: issues.append(("age", "warning", "العمر خارج النطاق المتوقع", ""))
        except ValueError:
            if not re.search(r"(سنه|سنة|شهر|يوم|اشهر|أشهر)", normalize_arabic(age_raw)):
                issues.append(("age", "warning", "العمر ليس رقماً ولا صيغة عمر مفهومة", ""))
    if age_raw and normalize_arabic(age_raw) in {normalize_arabic(k) for k in GENDERS} and gender_raw.replace(".", "", 1).isdigit():
        issues.append(("age/gender", "blocking", "اشتباه تبديل بين عمودي العمر والجنس", "مراجعة القيمتين"))
    phone = re.sub(r"\D", "", _text(canonical.get("phone")))
    if not phone:
        issues.append(("phone", "info", "رقم الهاتف مفقود ويمكن استكماله لاحقاً", ""))
    elif len(phone) < 10 or len(phone) > 15:
        issues.append(("phone", "warning", "طول رقم الهاتف غير صالح", ""))
    for field, value in raw.items():
        if isinstance(value, str) and value.startswith("="):
            issues.append((field, "info", "القيمة الأصلية صيغة Excel؛ حُفظت مع قيمتها المحسوبة", ""))
    reasons.extend(item[2] for item in issues)
    return issues, reasons


@transaction.atomic
def analyze_workbook(file_path, digest, original_filename, user):
    duplicate = ImportBatch.objects.filter(file_hash=digest, status__in=["reviewing", "completed"]).first()
    if duplicate:
        return duplicate, False
    previous = ImportBatch.objects.filter(original_filename=original_filename).order_by("-created_at").first()
    batch = ImportBatch.objects.create(file_hash=digest, original_filename=original_filename, file_size=file_path.stat().st_size, status="processing", imported_by=user, previous_batch=previous)
    ImportFile.objects.create(batch=batch, file_path=str(file_path), file_hash=digest)
    workbook = load_workbook(file_path, read_only=True, data_only=False, keep_links=False)
    value_workbook = load_workbook(file_path, read_only=True, data_only=True, keep_links=False)
    known_hashes = set(SourceRow.objects.exclude(batch=batch).values_list("row_hash", flat=True))
    previous_index = {}
    if previous:
        previous_index = {
            (sheet_name, row_number): row_hash
            for sheet_name, row_number, row_hash in previous.rows.select_related("sheet").values_list(
                "sheet__sheet_name", "original_row_number", "row_hash"
            )
        }
    current_hashes, name_index = set(), {}
    total = valid = flagged = 0
    try:
        for sheet_index, ws in enumerate(workbook.worksheets):
            value_ws = value_workbook.worksheets[sheet_index]
            header_row = _detect_header(ws)
            profile = SHEET_PROFILES.get(normalize_arabic(ws.title))
            headers = [item[0] for item in profile] if profile else _headers(ws, header_row)
            if not headers:
                continue
            mapping = {item[0]: item[1] for item in profile} if profile else {header: _canonical_header(header) for header in headers if _canonical_header(header)}
            sheet = ImportSheet.objects.create(batch=batch, sheet_name=ws.title, sheet_index=sheet_index, header_row=header_row, first_data_row=header_row + 1, total_rows=ws.max_row, column_mapping=mapping)
            row_count = 0
            formula_rows = ws.iter_rows(min_row=header_row + 1, values_only=True)
            cached_rows = value_ws.iter_rows(min_row=header_row + 1, values_only=True)
            for row_number, (values, cached_values) in enumerate(zip(formula_rows, cached_rows, strict=False), header_row + 1):
                values = values[:len(headers)]
                cached_values = cached_values[:len(headers)]
                raw = {headers[i]: _json_value(value) for i, value in enumerate(values) if i < len(headers) and value not in (None, "")}
                if not raw:
                    continue
                evaluated = {
                    headers[i]: _json_value(cached_values[i])
                    for i, value in enumerate(values)
                    if i < len(headers) and isinstance(value, str) and value.startswith("=") and cached_values[i] is not None
                }
                canonical = {mapping[key]: evaluated.get(key, value) for key, value in raw.items() if key in mapping}
                if profile and not _text(canonical.get("name")):
                    # الأوراق الأربع تحتوي أسطراً حسابية بعد البيانات؛ الاسم هو علامة السجل الفعلي.
                    continue
                meaningful = [key for key in canonical if key != "sequence" and _text(canonical[key])]
                if not meaningful:
                    continue
                normalized_name = normalize_arabic(canonical.get("name"))
                payload = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
                row_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                issues, reasons = _validate(canonical, raw)
                old_hash = previous_index.get((ws.title, row_number))
                if old_hash and old_hash != row_hash:
                    issues.append(("__row__", "warning", "تغيّر هذا الصف مقارنة بالنسخة السابقة من الملف", "راجع الفروق قبل الاعتماد"))
                    reasons.append("صف قديم عُدّل في نسخة Excel الجديدة")
                classification = "blocking" if any(issue[1] == "blocking" for issue in issues) else ("review" if any(issue[1] == "warning" for issue in issues) else "ready")
                previous_row = None
                if classification != "blocking" and (row_hash in known_hashes or row_hash in current_hashes):
                    classification, reasons = "duplicate", reasons + ["الصف مطابق تماماً لسجل مصدري سابق"]
                elif classification not in {"blocking", "review"} and normalized_name and normalized_name in name_index:
                    previous_row = name_index[normalized_name]
                    if previous_row.sheet_id != sheet.pk or _text(canonical.get("date")):
                        classification, reasons = "repeat_visit", reasons + ["الاسم نفسه ظهر في خدمة أو تاريخ آخر؛ يحتاج ربطاً بشرياً"]
                    else:
                        classification, reasons = "duplicate", reasons + ["الاسم نفسه مكرر دون معرّف كافٍ للحسم"]
                source = SourceRow.objects.create(batch=batch, sheet=sheet, original_row_number=row_number, raw_data={"source": raw, "evaluated": evaluated, "canonical": canonical}, row_hash=row_hash, classification=classification, flag_reasons=list(dict.fromkeys(reasons)), normalized_name=normalized_name, issues_count=len(issues))
                DataIssue.objects.bulk_create([DataIssue(source_row=source, field_name=field, original_value=_text(canonical.get(field, raw.get(field, ""))), issue_type="error" if severity == "blocking" else severity, severity=severity, description=description, suggested_value=suggestion, is_auto_fixable=False) for field, severity, description, suggestion in issues])
                if previous_row:
                    MatchCandidate.objects.create(source_row_a=previous_row, source_row_b=source, match_score=0.75, match_reason=reasons[-1])
                current_hashes.add(row_hash)
                if normalized_name: name_index.setdefault(normalized_name, source)
                total += 1; row_count += 1
                if classification == "ready": valid += 1
                else: flagged += 1
            sheet.actual_data_rows = row_count
            sheet.save(update_fields=["actual_data_rows"])
        batch.total_rows, batch.valid_rows, batch.issue_rows = total, valid, flagged
        batch.status, batch.completed_at = "reviewing", timezone.now()
        batch.save(update_fields=["total_rows", "valid_rows", "issue_rows", "status", "completed_at"])
        return batch, True
    except Exception as exc:
        batch.status, batch.notes = "failed", str(exc)[:1000]
        batch.save(update_fields=["status", "notes"])
        raise
    finally:
        workbook.close()
        value_workbook.close()
