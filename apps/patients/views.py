from io import BytesIO
from datetime import date

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from apps.core.models import Department, Notification, ReferenceValue
from apps.core.utils import log_audit, roles_required

from .forms import PatientForm
from .models import Patient
from .services import create_patient, find_patient_candidates, normalize_arabic_text, update_patient


@login_required
def patient_list(request, source_only=None):
    from apps.importer.models import SourceRow
    from apps.visits.models import Visit

    query = request.GET.get("q", "").strip()
    phone_query = request.GET.get("phone", "").strip()
    age_query = request.GET.get("age", "").strip()
    patients = Patient.objects.select_related("primary_name").prefetch_related(
        "contacts",
        "addresses",
        Prefetch(
            "visits",
            queryset=Visit.objects.select_related("department", "doctor_reference", "organizer_reference").order_by("-visit_date"),
            to_attr="_prefetched_visits",
        ),
        Prefetch(
            "source_rows",
            queryset=SourceRow.objects.select_related("sheet").order_by("-batch_id", "-original_row_number"),
            to_attr="_prefetched_source_rows",
        ),
    )
    if query:
        normalized_query = normalize_arabic_text(query)
        patients = patients.filter(
            Q(internal_code__icontains=query) | Q(external_id__icontains=query) | Q(names__full_name__icontains=query)
            | Q(names__normalized_name__icontains=normalized_query)
            | Q(contacts__value__icontains=query) | Q(addresses__text__icontains=query)
        ).distinct()
    if phone_query:
        digits = "".join(character for character in phone_query if character.isdigit())
        patients = patients.filter(contacts__value__icontains=digits[-10:]).distinct()
    if age_query.isdigit():
        age = min(int(age_query), 150)
        today = date.today()
        newest = date(today.year - age, today.month, min(today.day, 28))
        oldest = date(today.year - age - 1, today.month, min(today.day, 28))
        patients = patients.filter(Q(approx_age_value=age) | Q(date_of_birth__gt=oldest, date_of_birth__lte=newest))
    if source_only in {"manual", "excel"}:
        patients = patients.filter(source_type=source_only)
    elif request.GET.get("source") in {"manual", "excel"}:
        patients = patients.filter(source_type=request.GET["source"])
    if request.GET.get("department"):
        patients = patients.filter(visits__department_id=request.GET["department"])
    if request.GET.get("doctor"):
        patients = patients.filter(visits__doctor_reference_id=request.GET["doctor"])
    if request.GET.get("organizer"):
        patients = patients.filter(visits__organizer_reference_id=request.GET["organizer"])
    if request.GET.get("gender"):
        patients = patients.filter(gender=request.GET["gender"])
    if request.GET.get("status"):
        patients = patients.filter(visits__diagnosis__icontains=request.GET["status"])
    patients = patients.distinct()
    page = Paginator(patients, 30).get_page(request.GET.get("page"))
    change_state = Patient.objects.aggregate(latest=Max("updated_at"), total=Count("id"))
    return render(request, "patients/list.html", {
        "page": page,
        "query": query,
        "phone_query": phone_query,
        "age_query": age_query,
        "departments": Department.objects.filter(is_active=True),
        "doctors": ReferenceValue.objects.filter(category="doctor", is_active=True),
        "organizers": ReferenceValue.objects.filter(category="organizer", is_active=True),
        "diagnoses": ReferenceValue.objects.filter(category="diagnosis", is_active=True)[:250],
        "gender_choices": Patient.GENDER_CHOICES,
        "filters": request.GET,
        "change_token": f"{change_state['latest'].isoformat() if change_state['latest'] else ''}|{change_state['total']}",
        "source_only": source_only,
    })


@login_required
def imported_patient_list(request):
    return patient_list(request, source_only="excel")


@login_required
def patient_changes(request):
    state = Patient.objects.aggregate(latest=Max("updated_at"), total=Count("id"))
    token = f"{state['latest'].isoformat() if state['latest'] else ''}|{state['total']}"
    return JsonResponse({"changed": token != request.GET.get("token", ""), "token": token, "total": state["total"]})


@login_required
def patient_search(request):
    """بحث حي من أول حرف، منفصل عن كشف التكرار أثناء التسجيل."""
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})
    normalized = normalize_arabic_text(query)
    patients = Patient.objects.select_related("primary_name").prefetch_related("contacts").filter(
        Q(internal_code__icontains=query)
        | Q(external_id__icontains=query)
        | Q(names__normalized_name__icontains=normalized)
        | Q(contacts__value__icontains=query)
    ).distinct()[:12]
    return JsonResponse({"results": [{
        "id": str(item.pk), "code": item.internal_code, "name": item.display_name,
        "phone": item.contacts.filter(is_primary=True).values_list("value", flat=True).first() or "—",
        "age": item.calculated_age, "gender": item.gender,
        "url": reverse("patients:detail", args=[item.pk]),
    } for item in patients]})


@login_required
def patient_match(request):
    name = request.GET.get("name", "").strip()
    phone = "".join(character for character in request.GET.get("phone", "") if character.isdigit())
    age = request.GET.get("age", "").strip()
    matches = find_patient_candidates(
        name=name, phone=phone, age=age,
        birth_date=request.GET.get("birth_date") or None,
        gender=request.GET.get("gender", ""), address=request.GET.get("address", ""),
    )
    return JsonResponse({"results": [{
        "id": str(item["patient"].pk), "code": item["patient"].internal_code,
        "name": item["patient"].display_name, "phone": item["phone"], "age": item["age"],
        "gender": item["patient"].get_gender_display(),
        "birth_date": item["patient"].date_of_birth.isoformat() if item["patient"].date_of_birth else "",
        "address": item["address"] or "—", "score": item["score"], "reasons": item["reasons"],
        "department": item["latest_visit"].department.name if item["latest_visit"] and item["latest_visit"].department else "—",
        "last_visit": item["latest_visit"].visit_date.date().isoformat() if item["latest_visit"] else "",
        "source": "مستورد" if item["patient"].source_type == "excel" else "مسجل يدوياً",
        "visit_url": reverse("visits:create_for_patient", args=[item["patient"].pk]),
        "patient_url": reverse("patients:detail", args=[item["patient"].pk]),
        "edit_url": reverse("patients:edit", args=[item["patient"].pk]),
    } for item in matches]})


def _patient_initial(patient):
    visit = patient.latest_visit
    diagnosis = None
    if visit and visit.diagnosis:
        diagnosis = ReferenceValue.objects.filter(category="diagnosis", canonical_name=visit.diagnosis).first()
    return {
        "full_name": patient.display_name,
        "gender": patient.gender,
        "date_of_birth": patient.date_of_birth,
        "approx_age_value": patient.approx_age_value,
        "approx_age_unit": patient.approx_age_unit,
        "phone": patient.contacts.filter(is_primary=True).values_list("value", flat=True).first() or "",
        "address": patient.addresses.values_list("text", flat=True).first() or "",
        "external_id": patient.external_id,
        "department": visit.department_id if visit else None,
        "doctor_reference": visit.doctor_reference_id if visit else None,
        "organizer_reference": visit.organizer_reference_id if visit else None,
        "visit_date": visit.visit_date.date() if visit else None,
        "diagnosis_reference": diagnosis.pk if diagnosis else None,
        "chief_complaint": visit.chief_complaint if visit else "",
        "notes": visit.notes if visit else "",
    }


def _may_edit(user):
    return bool(user.is_owner or user.is_organizer or user.is_auditor)


@login_required
def patient_drawer(request, pk):
    patient = get_object_or_404(Patient.objects.select_related("primary_name").prefetch_related("contacts", "addresses", "visits"), pk=pk)
    can_edit = _may_edit(request.user)
    if request.method == "POST" and not can_edit:
        return JsonResponse({"ok": False, "message": "لا تملك صلاحية تعديل ملف المريض."}, status=403)
    form = PatientForm(
        request.POST or None,
        initial=None if request.method == "POST" else _patient_initial(patient),
        require_complete=False,
        department=(request.POST.get("department") if request.method == "POST" else (_patient_initial(patient).get("department"))),
        language=getattr(request, "LANGUAGE_CODE", "ar"),
    )
    if request.method == "POST" and form.is_valid():
        update_patient(patient, form.cleaned_data)
        log_audit(request, "update", "Patient", patient.pk, patient.internal_code)
        Notification.objects.create(
            user=request.user, event_type="patient_updated", title="تم تحديث ملف مريض",
            message=patient.internal_code, object_type="Patient", object_id=str(patient.pk),
            target_url=reverse("patients:list") + f"?patient={patient.pk}",
        )
        return JsonResponse({
            "ok": True,
            "message": "تم حفظ التغييرات بنجاح.",
            "patient": {
                "name": patient.display_name,
                "gender": patient.get_gender_display(),
                "age": patient.calculated_age,
                "phone": patient.contacts.filter(is_primary=True).values_list("value", flat=True).first() or "—",
            },
        })
    html = render_to_string("patients/_drawer.html", {"patient": patient, "form": form, "can_edit": can_edit}, request=request)
    return HttpResponse(html, status=422 if request.method == "POST" else 200)


@login_required
def doctors_for_department(request):
    department_id = request.GET.get("department")
    doctors = ReferenceValue.objects.filter(category="doctor", is_active=True, departments__pk=department_id).distinct() if department_id else ReferenceValue.objects.none()
    return JsonResponse({"results": [{"id": item.pk, "text": item.canonical_name} for item in doctors]})


@roles_required("organizer", "data_auditor")
def patient_create(request):
    form = PatientForm(request.POST or None, require_complete=True, language=getattr(request, "LANGUAGE_CODE", "ar")).apply_widget_classes()
    if request.method == "POST" and form.is_valid():
        candidates = find_patient_candidates(
            name=form.cleaned_data["full_name"], phone=form.cleaned_data.get("phone", ""),
            age=form.cleaned_data.get("approx_age_value"), birth_date=form.cleaned_data.get("date_of_birth"),
            gender=form.cleaned_data.get("gender", ""), address=form.cleaned_data.get("address", ""),
        )
        if candidates and request.POST.get("duplicate_override") != "1":
            return render(request, "shared/form.html", {
                "form": form, "title": "تسجيل مريض جديد", "submit_label": "حفظ ملف المريض",
                "duplicate_candidates": candidates,
            })
        patient = create_patient(form.cleaned_data, request.user)
        log_audit(request, "create", "Patient", patient.pk, patient.internal_code)
        Notification.objects.create(user=request.user, event_type="patient_created", title="تم تسجيل مريض جديد", message=patient.internal_code, object_type="Patient", object_id=str(patient.pk), target_url=reverse("patients:list") + f"?patient={patient.pk}")
        messages.success(request, f"تم إنشاء ملف المريض بالرقم {patient.internal_code}.")
        return redirect("patients:detail", pk=patient.pk)
    return render(request, "shared/form.html", {"form": form, "title": "تسجيل مريض جديد", "submit_label": "حفظ ملف المريض"})


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient.objects.select_related("primary_name"), pk=pk)
    log_audit(request, "view", "Patient", patient.pk, patient.internal_code)
    return render(request, "patients/detail.html", {"patient": patient})


@roles_required("organizer", "data_auditor")
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    initial = _patient_initial(patient)
    form = PatientForm(request.POST or None, initial=initial, require_complete=False, department=initial.get("department"), language=getattr(request, "LANGUAGE_CODE", "ar")).apply_widget_classes()
    if request.method == "POST" and form.is_valid():
        update_patient(patient, form.cleaned_data)
        log_audit(request, "update", "Patient", patient.pk, patient.internal_code)
        messages.success(request, "تم تحديث ملف المريض مع حفظ العملية في سجل التدقيق.")
        return redirect("patients:detail", pk=patient.pk)
    return render(request, "shared/form.html", {"form": form, "title": f"تعديل {patient.internal_code}", "submit_label": "حفظ التعديلات"})


@roles_required("data_auditor")
def patient_archive(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        patient.soft_delete()
        log_audit(request, "delete", "Patient", patient.pk, patient.internal_code)
        messages.success(request, "تمت أرشفة الملف دون حذفه نهائياً.")
    return redirect("patients:list")


@login_required
def patient_qr(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    image = qrcode.make(f"CLINIC:PATIENT:{patient.pk}")
    output = BytesIO(); image.save(output, format="PNG")
    return HttpResponse(output.getvalue(), content_type="image/png")


@roles_required("data_auditor")
def patient_trash(request):
    patients = Patient.all_objects.dead().select_related("primary_name").prefetch_related("names", "contacts")
    return render(request, "patients/trash.html", {"patients": patients[:250]})


@roles_required("data_auditor")
def patient_restore(request, pk):
    patient = get_object_or_404(Patient.all_objects.dead(), pk=pk)
    if request.method == "POST":
        patient.restore()
        log_audit(request, "restore", "Patient", patient.pk, patient.internal_code)
        messages.success(request, "تمت استعادة ملف المريض من سلة المحذوفات.")
    return redirect("patients:trash")
