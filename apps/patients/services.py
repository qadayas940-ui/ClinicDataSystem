import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Patient, PatientAddress, PatientContact, PatientName, PatientSequence


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
    )
    name = PatientName.objects.create(patient=patient, full_name=cleaned_data["full_name"].strip(), is_primary=True, source="manual")
    patient.primary_name = name
    patient.save(update_fields=["primary_name", "updated_at"])
    phone = normalize_phone(cleaned_data.get("phone"))
    if phone:
        PatientContact.objects.create(patient=patient, value=phone, contact_type="mobile", is_primary=True)
    address = (cleaned_data.get("address") or "").strip()
    if address:
        PatientAddress.objects.create(patient=patient, text=address, address_type="سكن")
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
        name.save(update_fields=["full_name", "updated_at"])
    else:
        name = PatientName.objects.create(patient=patient, full_name=cleaned_data["full_name"].strip(), is_primary=True, source="manual")
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
    return patient
