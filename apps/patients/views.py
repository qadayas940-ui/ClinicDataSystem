from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.utils import log_audit, roles_required

from .forms import PatientForm
from .models import Patient
from .services import create_patient, update_patient


@login_required
def patient_list(request):
    query = request.GET.get("q", "").strip()
    patients = Patient.objects.select_related("primary_name").prefetch_related("contacts")
    if query:
        patients = patients.filter(
            Q(internal_code__icontains=query) | Q(names__full_name__icontains=query)
            | Q(contacts__value__icontains=query) | Q(addresses__text__icontains=query)
        ).distinct()
    page = Paginator(patients, 30).get_page(request.GET.get("page"))
    return render(request, "patients/list.html", {"page": page, "query": query})


@roles_required("organizer", "data_auditor")
def patient_create(request):
    form = PatientForm(request.POST or None).apply_widget_classes()
    if request.method == "POST" and form.is_valid():
        patient = create_patient(form.cleaned_data, request.user)
        log_audit(request, "create", "Patient", patient.pk, patient.internal_code)
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
    initial = {
        "full_name": patient.display_name, "gender": patient.gender,
        "date_of_birth": patient.date_of_birth, "approx_age_value": patient.approx_age_value,
        "approx_age_unit": patient.approx_age_unit,
        "phone": patient.contacts.filter(is_primary=True).values_list("value", flat=True).first() or "",
        "address": patient.addresses.values_list("text", flat=True).first() or "",
    }
    form = PatientForm(request.POST or None, initial=initial).apply_widget_classes()
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
