import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
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
    "external_id": {"المعرف الخارجي", "الرقم التعريفي الخارجي", "external id", "external_id"},
}
GENDERS = {
    "ذكر": "male", "رجل": "male", "ذكور": "male", "ذ": "male", "male": "male", "man": "male", "m": "male",
    "انثى": "female", "أنثى": "female", "امراه": "female", "امرأة": "female", "نساء": "female",
    "ا": "female", "female": "female", "woman": "female", "f": "female",
    "غير محدد": "unknown", "غير معروف": "unknown", "unknown": "unknown", "u": "unknown",
}
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
IMPORT_REPAIR_MARKER = "[import-repair-v1.4-complete]"


def _text(value):
    return "" if value is None else re.sub(r"\s+", " ", str(value)).strip()


def normalize_arabic(value):
    value = _text(value).lower()
    return value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}))


REFERENCE_FIELDS = {
    "department": "department",
    "doctor": "doctor",
    "organizer": "organizer",
    "test": "lab_test",
    "status": "diagnosis",
    "address": "area",
}


def _reference_identity(category, value):
    """يوحّد الفروق الشكلية المؤكدة فقط، ويترك التشابه الغامض للمراجعة."""
    display = _text(value)
    if category == "doctor":
        display = re.sub(r"^(?:د\s*[./-]?|دكتور(?:ة)?)\s*", "", display, flags=re.IGNORECASE).strip()
        display = f"د. {display}" if display else ""
    elif category == "lab_test":
        display = display.upper()
    normalized = normalize_arabic(display)
    normalized = re.sub(r"[\s._/\\-]+", " ", normalized).strip()
    return display, normalized


def _remember_reference(index, category, value, sheet_name, departments=None):
    display, normalized = _reference_identity(category, value)
    if not display or not normalized:
        return
    item = index[(category, normalized)]
    item["canonical_name"] = item.get("canonical_name") or display
    item["aliases"].add(_text(value))
    item["source_sheets"].add(sheet_name)
    item["occurrence_count"] += 1
    item["departments"].update(_text(name) for name in (departments or []) if _text(name))


def _doctor_parts(value, row_department=""):
    """يفصل اسم الطبيب عن تخصص مكتوب بعد / ولا يحوّل اسم القسم إلى طبيب."""
    parts = re.split(r"\s*\+\s*", _text(value))
    known_departments = {normalize_arabic(name) for name in (
        "نسائية", "نسائية وتوليد", "اطفال", "أطفال", "بصريات", "عيون", "سونار",
        "جراحة عظام", "عظام", "باطنية", "جراحة عامة", "جلدية", "مفاصل",
        "طب اسرة", "طب أسرة", "قلبية", "اذن وحنجرة", "أذن وحنجرة",
    )}
    result = []
    for part in parts:
        chunks = [chunk.strip() for chunk in re.split(r"\s*/\s*", part, maxsplit=1)]
        name = chunks[0]
        departments = [_text(row_department)] if _text(row_department) else []
        if len(chunks) > 1 and chunks[1]:
            departments.append(chunks[1])
        normalized_name = normalize_arabic(re.sub(r"^(?:د\s*[./-]?|دكتور(?:ة)?)\s*", "", name).strip())
        if not normalized_name or normalized_name in known_departments:
            continue
        result.append((name, departments))
    return result


def _sync_reference_values(index):
    from apps.core.models import Department, ReferenceValue

    department_lookup = {}
    for (category, normalized), data in index.items():
        if category != "department":
            continue
        code = "XLS-" + hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8].upper()
        department, _ = Department.all_objects.update_or_create(
            code=code,
            defaults={"name": data["canonical_name"], "department_type": "clinic", "is_active": True, "deleted_at": None},
        )
        department_lookup[normalized] = department
    for (category, normalized), data in index.items():
        aliases = sorted(data["aliases"])
        needs_review = len(aliases) > 1 or len(normalized) < 3
        item, created = ReferenceValue.all_objects.get_or_create(
            category=category,
            normalized_name=normalized,
            defaults={
                "canonical_name": data["canonical_name"],
                "aliases": aliases,
                "source_sheets": sorted(data["source_sheets"]),
                "occurrence_count": data["occurrence_count"],
                "needs_review": needs_review,
            },
        )
        if not created:
            item.canonical_name = data["canonical_name"]
            item.aliases = sorted(set(item.aliases) | set(aliases))
            item.source_sheets = sorted(set(item.source_sheets) | data["source_sheets"])
            item.occurrence_count += data["occurrence_count"]
            item.needs_review = item.needs_review or needs_review
            item.deleted_at = None
            item.save(update_fields=["canonical_name", "aliases", "source_sheets", "occurrence_count", "needs_review", "deleted_at", "updated_at"])
        if category == "department":
            department_lookup.setdefault(normalized, Department.objects.filter(name=data["canonical_name"]).first())
        if category == "doctor":
            linked = []
            for department_name in data["departments"]:
                dep_normalized = normalize_arabic(department_name)
                department = department_lookup.get(dep_normalized) or Department.objects.filter(name__iexact=department_name).first()
                if department:
                    linked.append(department)
            item.departments.set(linked)


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
    incoming = Path(settings.DATA_PATH) / "Files" / "Imported" / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    temp_path = incoming / f"upload-{timezone.now().strftime('%Y%m%d%H%M%S%f')}.xlsx"
    with temp_path.open("wb") as output:
        for chunk in uploaded_file.chunks(): output.write(chunk)
    digest = _file_hash(temp_path)
    archive = Path(settings.DATA_PATH) / "Files" / "Imported" / digest[:2]
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
    elif not (re.fullmatch(r"07[578]\d{8}", phone) or re.fullmatch(r"9647[578]\d{8}", phone)):
        issues.append(("phone", "warning", "رقم الهاتف ليس عراقياً صحيحاً من 11 رقماً", "مثال: 07899189225"))
    for field, value in raw.items():
        if isinstance(value, str) and value.startswith("="):
            issues.append((field, "info", "القيمة الأصلية صيغة Excel؛ حُفظت مع قيمتها المحسوبة", ""))
    reasons.extend(item[2] for item in issues)
    return issues, reasons


def _repair_swapped_age_gender(canonical):
    """Repair rows where the legacy workbook swaps age/gender columns mid-sheet."""
    age = normalize_arabic(canonical.get("age"))
    gender = _text(canonical.get("gender"))
    if age in {normalize_arabic(key) for key in GENDERS} and re.fullmatch(r"\d+(?:\.0+)?", gender):
        canonical["age"], canonical["gender"] = canonical.get("gender"), canonical.get("age")
    return canonical


@transaction.atomic
def analyze_workbook(file_path, digest, original_filename, user, import_type="patients"):
    duplicate = ImportBatch.objects.filter(file_hash=digest, import_type=import_type, status__in=["reviewing", "completed"]).first()
    if duplicate:
        return duplicate, False
    previous = ImportBatch.objects.filter(original_filename=original_filename).order_by("-created_at").first()
    batch = ImportBatch.objects.create(file_hash=digest, original_filename=original_filename, file_size=file_path.stat().st_size, import_type=import_type, status="processing", imported_by=user, previous_batch=previous)
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
    reference_index = defaultdict(lambda: {"aliases": set(), "source_sheets": set(), "occurrence_count": 0, "departments": set()})
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
                canonical = _repair_swapped_age_gender(canonical)
                if profile and not _text(canonical.get("name")):
                    # الأوراق الأربع تحتوي أسطراً حسابية بعد البيانات؛ الاسم هو علامة السجل الفعلي.
                    continue
                meaningful = [key for key in canonical if key != "sequence" and _text(canonical[key])]
                if not meaningful:
                    continue
                for field_name, value in canonical.items():
                    category = REFERENCE_FIELDS.get(field_name)
                    if normalize_arabic(ws.title) in {"احالات", "الاحالات"} and field_name == "doctor":
                        _remember_reference(reference_index, "referral_destination", value, ws.title)
                        for doctor_name, departments in _doctor_parts(value):
                            _remember_reference(reference_index, "doctor", doctor_name, ws.title, departments)
                        continue
                    if field_name == "doctor":
                        for doctor_name, departments in _doctor_parts(value, canonical.get("department", "")):
                            _remember_reference(reference_index, "doctor", doctor_name, ws.title, departments)
                        continue
                    if category:
                        _remember_reference(reference_index, category, value, ws.title)
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
        _sync_reference_values(reference_index)
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


def remap_sheet(sheet, mapping):
    """يعيد بناء الحقول المعروفة مع إبقاء كل عمود غير معروف داخل البيانات الإضافية."""
    sheet.column_mapping = mapping
    sheet.save(update_fields=["column_mapping"])
    for row in sheet.rows.prefetch_related("issues"):
        source = row.raw_data.get("source", {})
        canonical = {}
        additional = {}
        for header, value in source.items():
            target = mapping.get(header, "")
            if target:
                canonical[target] = value
            else:
                additional[header] = value
        row.raw_data["canonical"] = canonical
        row.raw_data["additional"] = additional
        issues, reasons = _validate(canonical, source)
        preserved = row.classification in {"duplicate", "repeat_visit"}
        if not preserved:
            row.classification = "blocking" if any(issue[1] == "blocking" for issue in issues) else ("review" if any(issue[1] == "warning" for issue in issues) else "ready")
        row.flag_reasons = reasons
        row.normalized_name = normalize_arabic(canonical.get("name"))
        row.issues_count = len(issues)
        row.save(update_fields=["raw_data", "classification", "flag_reasons", "normalized_name", "issues_count"])
        row.issues.all().delete()
        DataIssue.objects.bulk_create([
            DataIssue(
                source_row=row, field_name=field,
                original_value=_text(canonical.get(field, source.get(field, ""))),
                issue_type="error" if severity == "blocking" else severity,
                severity=severity, description=description,
                suggested_value=suggestion, is_auto_fixable=False,
            )
            for field, severity, description, suggestion in issues
        ])
    batch = sheet.batch
    batch.total_rows = batch.rows.count()
    batch.valid_rows = batch.rows.filter(classification="ready").count()
    batch.issue_rows = batch.total_rows - batch.valid_rows
    batch.save(update_fields=["total_rows", "valid_rows", "issue_rows"])


def _reference(category, value):
    if not _text(value):
        return None
    _, normalized = _reference_identity(category, value)
    from apps.core.models import ReferenceValue

    return ReferenceValue.objects.filter(category=category, normalized_name=normalized, is_active=True).first()


def _department(value):
    if not _text(value):
        return None
    from apps.core.models import Department, ReferenceValue

    normalized = normalize_arabic(value)
    ref = ReferenceValue.objects.filter(category="department", normalized_name=normalized).first()
    if ref:
        return Department.objects.filter(name=ref.canonical_name, is_active=True).first()
    return Department.objects.filter(name__iexact=_text(value), is_active=True).first()


def _age(value):
    match = re.search(r"\d+(?:\.\d+)?", _text(value))
    if not match:
        return None, ""
    number = max(0, min(150, int(float(match.group()))))
    normalized = normalize_arabic(value)
    unit = "month" if "شهر" in normalized else ("day" if "يوم" in normalized else "year")
    return number, unit


def _positive_count(value):
    match = re.search(r"\d+", _text(value))
    return max(0, min(100000, int(match.group()))) if match else 0


def source_repeat_count(raw_data):
    """Read COUNTIF's cached result, never the row number embedded in its formula."""
    canonical = raw_data.get("canonical", {})
    direct = canonical.get("repeat_count")
    if isinstance(direct, (int, float)):
        return _positive_count(direct)
    evaluated = raw_data.get("evaluated", {})
    for header, value in evaluated.items():
        if _canonical_header(header) == "repeat_count" and isinstance(value, (int, float)):
            return _positive_count(value)
    source = raw_data.get("source", {})
    for header, value in source.items():
        if _canonical_header(header) == "repeat_count" and isinstance(value, (int, float)):
            return _positive_count(value)
    return 0


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    return parse_date(text[:10]) if text else None


def _match_existing_patient(name, phone, birth_date, gender, address):
    """مطابقة محافظة: الهاتف أولاً، ثم مجموعة متطابقة بخصائص مستقرة؛ لا تدمج الغامض."""
    from apps.patients.models import Patient

    if phone:
        phone_matches = Patient.objects.filter(contacts__value=phone).distinct()
        if phone_matches.count() == 1:
            return phone_matches.first()
    from apps.patients.services import normalize_arabic_text

    candidates = Patient.objects.filter(names__normalized_name=normalize_arabic_text(name)).distinct()
    # Excel's COUNTIF treats every row carrying the same normalized full name
    # as one history. Prefer the imported card before filtering inconsistent
    # age, gender or address values from the different workbook sheets.
    imported_candidate = candidates.filter(source_type="excel").order_by("created_at", "pk").first()
    if imported_candidate:
        return imported_candidate
    if birth_date:
        candidates = candidates.filter(date_of_birth=birth_date)
    if gender and gender != "unknown":
        candidates = candidates.filter(gender=gender)
    if address:
        address_matches = candidates.filter(addresses__text__iexact=address).distinct()
        if address_matches.count() == 1:
            return address_matches.first()
    if candidates.count() == 1:
        return candidates.first()
    return None


@transaction.atomic
def import_batch_records(batch, user, source_row=None):
    """ينشئ السجلات القابلة للاستيراد دون دمج أو حذف، ويحفظ مصدر كل قيمة."""
    from apps.core.models import Notification
    from apps.laboratory.models import LabOrder, LabOrderTest
    from apps.patients.forms import normalize_iraqi_mobile
    from apps.patients.services import create_patient
    from apps.referrals.models import Referral

    if batch.import_type != "patients" and source_row is None:
        batch.status = "completed"
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "completed_at"])
        Notification.objects.create(
            user=user, event_type="import_completed", title="اكتمل إدراج القاموس المرجعي",
            message=f"تم تحديث بيانات {batch.get_import_type_display() if hasattr(batch, 'get_import_type_display') else batch.import_type} من {batch.original_filename}",
            object_type="ImportBatch", object_id=str(batch.pk), target_url=reverse("importer:batch_detail", args=[batch.pk]),
        )
        return 0

    rows = batch.rows.select_related("sheet").filter(linked_patient__isnull=True).exclude(status="rejected")
    if source_row is not None:
        rows = rows.filter(pk=source_row.pk)
    imported = 0
    for row in rows.iterator(chunk_size=500):
        canonical = _repair_swapped_age_gender(dict(row.raw_data.get("canonical", {})))
        name = _text(canonical.get("name"))
        if not name:
            continue
        age_value, age_unit = _age(canonical.get("age"))
        gender = GENDERS.get(normalize_arabic(canonical.get("gender")), "unknown")
        try:
            phone = normalize_iraqi_mobile(_text(canonical.get("phone")))
        except ValidationError:
            phone = ""
        doctor_parts = _doctor_parts(canonical.get("doctor", ""), canonical.get("department", ""))
        doctor = _reference("doctor", doctor_parts[0][0]) if doctor_parts else None
        organizer = _reference("organizer", canonical.get("organizer"))
        diagnosis = _reference("diagnosis", canonical.get("status"))
        source_date = _date(canonical.get("date"))
        birth_date = _date(canonical.get("birth_date"))
        imported_visit_count = source_repeat_count(row.raw_data)
        external_id = _text(canonical.get("external_id")) or (
            f"XLS-{batch.file_hash[:10].upper()}-{row.sheet.sheet_index + 1}-{row.original_row_number}"
        )
        payload = {
            "full_name": name,
            "gender": gender,
            "date_of_birth": birth_date,
            "approx_age_value": age_value,
            "approx_age_unit": age_unit,
            "phone": phone,
            "address": _text(canonical.get("address")),
            "external_id": external_id,
            "source_type": "excel",
            "source_file": batch.original_filename,
            "source_sheet": row.sheet.sheet_name,
            "source_row": row.original_row_number,
            "imported_at": timezone.now(),
            "imported_visit_count": imported_visit_count,
            "additional_data": {
                "source_columns": row.raw_data.get("source", {}),
                "unmapped_columns": row.raw_data.get("additional", {}),
                "imported_visit_count": imported_visit_count,
            },
        }
        sheet_name = normalize_arabic(row.sheet.sheet_name)
        if sheet_name == "مراجعه المرضي":
            payload.update({
                "department": _department(canonical.get("department")),
                "doctor_reference": doctor,
                "organizer_reference": organizer,
                "diagnosis_reference": diagnosis,
                "diagnosis": _text(canonical.get("status")),
                "chief_complaint": _text(canonical.get("status")),
                "notes": _text(canonical.get("notes")),
                "visit_date": source_date or timezone.localdate(),
                "visit_type": "imported_historical",
            })
        patient = _match_existing_patient(name, phone, birth_date, gender, payload["address"])
        if patient is None:
            patient = create_patient(payload, user)
        elif sheet_name == "مراجعه المرضي":
            from apps.visits.models import Visit

            Visit.objects.create(
                patient=patient,
                created_by=user,
                visit_date=timezone.make_aware(datetime.combine(source_date or timezone.localdate(), datetime.min.time())),
                visit_type="imported_historical",
                department=payload.get("department"),
                doctor_reference=doctor,
                organizer_reference=organizer,
                diagnosis=_text(canonical.get("status")),
                chief_complaint=_text(canonical.get("status")),
                notes=_text(canonical.get("notes")),
                source="excel",
            )
        if imported_visit_count > patient.imported_visit_count:
            patient.imported_visit_count = imported_visit_count
            patient.save(update_fields=["imported_visit_count", "updated_at"])
        if sheet_name == "المختبر":
            order = LabOrder.objects.create(patient=patient, order_date=timezone.now(), status="pending", notes=_text(canonical.get("notes")))
            if _text(canonical.get("test")):
                LabOrderTest.objects.create(lab_order=order, test_name=_text(canonical.get("test")))
        elif sheet_name in {"احالات", "الاحالات"}:
            Referral.objects.create(
                patient=patient, referring_doctor=None,
                destination_name=_text(canonical.get("doctor")),
                referral_date=timezone.now(), status="pending",
            )
        elif sheet_name == "عياده العيون":
            from apps.ophthalmology.models import EyeClinicVisit

            EyeClinicVisit.objects.create(
                patient=patient,
                visit_date=timezone.now(),
                notes=_text(canonical.get("notes")),
                status="open",
            )
        row.linked_patient = patient
        row.imported_at = timezone.now()
        row.status = "accepted"
        row.save(update_fields=["linked_patient", "imported_at", "status"])
        imported += 1
    if source_row is None:
        batch.status = "completed"
        batch.completed_at = timezone.now()
        if IMPORT_REPAIR_MARKER not in batch.notes:
            batch.notes = f"{batch.notes}\n{IMPORT_REPAIR_MARKER}".strip()
        batch.save(update_fields=["status", "completed_at", "notes"])
    Notification.objects.create(
        user=user, event_type="import_completed", title="اكتمل إدراج ملف Excel" if source_row is None else "تم إدراج سجل من Excel",
        message=f"تم إدراج {imported} سجل من {batch.original_filename}",
        object_type="ImportBatch", object_id=str(batch.pk), target_url=reverse("importer:batch_detail", args=[batch.pk]),
    )
    return imported
