import re
from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Patient, PatientAddress, PatientContact, PatientName, PatientSequence


def normalize_arabic_text(value):
    value = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", (value or "").lower())
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}))
    return re.sub(r"\s+", " ", value).strip()


def _numeric_age(patient):
    if patient.date_of_birth:
        today = timezone.localdate()
        return today.year - patient.date_of_birth.year - ((today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day))
    if patient.approx_age_unit == "year":
        return patient.approx_age_value
    return None


def find_patient_candidates(*, name="", phone="", age=None, birth_date=None, gender="", address="", limit=8):
    """يعيد مرشّحين مع درجة تفسيرية؛ لا يدمج ولا يغيّر أي سجل."""
    normalized_name = normalize_arabic_text(name)
    name_parts = [part for part in normalized_name.split(" ") if part]
    phone_digits = re.sub(r"\D", "", phone or "")
    if phone_digits.startswith("964"):
        phone_digits = phone_digits[3:]
    phone_tail = phone_digits[-10:]
    try:
        numeric_age = int(age) if age not in (None, "") else None
    except (TypeError, ValueError):
        numeric_age = None
    if isinstance(birth_date, str):
        birth_date = parse_date(birth_date)

    if len(name_parts) < 2 and len(phone_tail) < 7 and not birth_date:
        return []

    base = Patient.objects.select_related("primary_name").prefetch_related("contacts", "addresses", "visits__department", "visits__doctor_reference")
    criteria = Q()
    if len(name_parts) >= 2:
        criteria |= Q(names__normalized_name__icontains=" ".join(name_parts[:2]))
    if len(phone_tail) >= 7:
        criteria |= Q(contacts__value__icontains=phone_tail)
    if birth_date:
        criteria |= Q(date_of_birth=birth_date)

    candidates = []
    normalized_address = normalize_arabic_text(address)
    for patient in base.filter(criteria).distinct()[:50]:
        candidate_name = normalize_arabic_text(patient.display_name)
        candidate_phone = patient.contacts.filter(is_primary=True).values_list("value", flat=True).first() or ""
        candidate_address = patient.addresses.values_list("text", flat=True).first() or ""
        score, reasons = 0, []
        if normalized_name and candidate_name == normalized_name:
            score += 45; reasons.append("الاسم مطابق")
        elif len(name_parts) >= 2 and all(part in candidate_name.split(" ") for part in name_parts):
            score += 28; reasons.append("أجزاء الاسم متوافقة")
        elif len(name_parts) >= 2 and " ".join(name_parts[:2]) in candidate_name:
            score += 20; reasons.append("أول اسمين متوافقان")
        if len(phone_tail) >= 7 and re.sub(r"\D", "", candidate_phone).endswith(phone_tail):
            score += 55; reasons.append("الهاتف مطابق")
        if birth_date and patient.date_of_birth == birth_date:
            score += 45; reasons.append("تاريخ الميلاد مطابق")
        if gender and gender != "unknown" and patient.gender == gender:
            score += 10; reasons.append("الجنس مطابق")
        candidate_age = _numeric_age(patient)
        if numeric_age is not None and candidate_age is not None and abs(candidate_age - numeric_age) <= 1:
            score += 18; reasons.append("العمر متوافق")
        if normalized_address and normalize_arabic_text(candidate_address) == normalized_address:
            score += 15; reasons.append("المنطقة مطابقة")
        if score < 20:
            continue
        latest_visit = patient.latest_visit
        candidates.append({
            "patient": patient,
            "score": min(score, 100),
            "reasons": reasons,
            "phone": candidate_phone,
            "address": candidate_address,
            "age": patient.calculated_age,
            "latest_visit": latest_visit,
        })
    candidates.sort(key=lambda item: (-item["score"], item["patient"].display_name))
    return candidates[:limit]


def _visit_datetime(value):
    value = value or timezone.localdate()
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value)
    return timezone.make_aware(datetime.combine(value, time(hour=12)))


def _visit_payload(cleaned_data):
    diagnosis = cleaned_data.get("diagnosis_reference")
    return {
        "visit_date": _visit_datetime(cleaned_data.get("visit_date")),
        "visit_type": cleaned_data.get("visit_type", "clinic"),
        "department": cleaned_data.get("department"),
        "doctor_reference": cleaned_data.get("doctor_reference"),
        "organizer_reference": cleaned_data.get("organizer_reference"),
        "diagnosis": diagnosis.canonical_name if diagnosis else (cleaned_data.get("diagnosis") or ""),
        "chief_complaint": cleaned_data.get("chief_complaint", ""),
        "notes": cleaned_data.get("notes", ""),
    }


def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("964"):
        local = "0" + digits[3:]
    elif digits.startswith("7"):
        local = "0" + digits
    else:
        local = digits
    if not re.fullmatch(r"07[578]\d{8}", local):
        raise ValidationError("رقم الهاتف يجب أن يكون عراقياً صحيحاً من 11 رقم.")
    return "+964" + local[1:]


def _new_code():
    year = timezone.localdate().year
    if connection.vendor == "postgresql":
        # Prevent the first two concurrent registrations from racing to create
        # the same yearly sequence row. The subsequent row lock serializes IDs.
        table = connection.ops.quote_name(PatientSequence._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {table} (year, last_value) VALUES (%s, 0) ON CONFLICT (year) DO NOTHING",
                [year],
            )
        sequence = PatientSequence.objects.select_for_update().get(year=year)
    else:
        sequence, _ = PatientSequence.objects.select_for_update().get_or_create(year=year)
    sequence.last_value += 1
    sequence.save(update_fields=["last_value"])
    return f"CLN{str(year)[-2:]}-{sequence.last_value:010d}"


@transaction.atomic
def create_patient(cleaned_data, user):
    has_approx_age = cleaned_data.get("approx_age_value") is not None
    patient = Patient.objects.create(
        internal_code=_new_code(), gender=cleaned_data["gender"],
        date_of_birth=cleaned_data.get("date_of_birth"), approx_age_value=cleaned_data.get("approx_age_value"),
        approx_age_unit=cleaned_data.get("approx_age_unit", ""),
        approx_age_recorded_date=timezone.localdate() if has_approx_age else None,
        is_approx_age=has_approx_age, created_by=user,
        external_id=cleaned_data.get("external_id", ""),
        source_type=cleaned_data.get("source_type", "manual"),
        source_file=cleaned_data.get("source_file", ""),
        source_sheet=cleaned_data.get("source_sheet", ""),
        source_row=cleaned_data.get("source_row"),
        imported_at=cleaned_data.get("imported_at"),
        imported_visit_count=cleaned_data.get("imported_visit_count") or 0,
        additional_data=cleaned_data.get("additional_data") or {},
    )
    full_name = cleaned_data["full_name"].strip()
    name = PatientName.objects.create(patient=patient, full_name=full_name, normalized_name=normalize_arabic_text(full_name), is_primary=True, source=cleaned_data.get("source_type", "manual"))
    patient.primary_name = name
    patient.save(update_fields=["primary_name", "updated_at"])
    phone = normalize_phone(cleaned_data.get("phone"))
    if phone:
        PatientContact.objects.create(patient=patient, value=phone, contact_type="mobile", is_primary=True)
    address = (cleaned_data.get("address") or "").strip()
    if address:
        PatientAddress.objects.create(patient=patient, text=address, address_type="سكن")
    if any(cleaned_data.get(key) for key in ("department", "doctor_reference", "organizer_reference", "diagnosis_reference", "diagnosis", "chief_complaint", "notes", "visit_date")):
        from apps.visits.models import Visit

        Visit.objects.create(patient=patient, created_by=user, **_visit_payload(cleaned_data))
    return patient


@transaction.atomic
def update_patient(patient, cleaned_data):
    patient.gender = cleaned_data["gender"]
    patient.date_of_birth = cleaned_data.get("date_of_birth")
    patient.approx_age_value = cleaned_data.get("approx_age_value")
    patient.approx_age_unit = cleaned_data.get("approx_age_unit", "")
    patient.approx_age_recorded_date = timezone.localdate() if cleaned_data.get("approx_age_value") is not None else None
    patient.is_approx_age = cleaned_data.get("approx_age_value") is not None
    patient.save()
    name = patient.primary_name or patient.names.filter(is_primary=True).first()
    if name:
        name.full_name = cleaned_data["full_name"].strip()
        name.normalized_name = normalize_arabic_text(name.full_name)
        name.save(update_fields=["full_name", "normalized_name", "updated_at"])
    else:
        full_name = cleaned_data["full_name"].strip()
        name = PatientName.objects.create(patient=patient, full_name=full_name, normalized_name=normalize_arabic_text(full_name), is_primary=True, source="manual")
        patient.primary_name = name
        patient.save(update_fields=["primary_name", "updated_at"])
    phone = normalize_phone(cleaned_data.get("phone"))
    contact = patient.contacts.filter(is_primary=True).first()
    if phone and contact:
        contact.value = phone
        contact.save(update_fields=["value", "updated_at"])
    elif phone:
        PatientContact.objects.create(patient=patient, value=phone, contact_type="mobile", is_primary=True)
    address = (cleaned_data.get("address") or "").strip()
    current_address = patient.addresses.first()
    if address and current_address:
        current_address.text = address
        current_address.save(update_fields=["text", "updated_at"])
    elif address:
        PatientAddress.objects.create(patient=patient, text=address, address_type="سكن")
    if any(cleaned_data.get(key) for key in ("department", "doctor_reference", "organizer_reference", "diagnosis_reference", "diagnosis", "chief_complaint", "notes", "visit_date")):
        from apps.visits.models import Visit

        visit = patient.visits.first()
        payload = _visit_payload(cleaned_data)
        if visit:
            for key, value in payload.items():
                setattr(visit, key, value)
            visit.save()
        else:
            Visit.objects.create(patient=patient, created_by=patient.created_by, **payload)
    return patient
