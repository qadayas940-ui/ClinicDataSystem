from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.utils import log_audit, roles_required
from apps.patients.models import Patient

from .forms import LabOrderForm
from .models import LabOrder, LabOrderTest


@login_required
def order_list(request):
    orders = LabOrder.objects.select_related(
        "patient", "patient__primary_name", "requesting_doctor", "requesting_doctor_reference"
    ).prefetch_related("tests")
    if request.GET.get("patient"): orders = orders.filter(patient_id=request.GET["patient"])
    return render(request, "laboratory/list.html", {"page": Paginator(orders, 30).get_page(request.GET.get("page"))})


@roles_required("doctor", "organizer")
@transaction.atomic
def order_create(request, patient_id=None):
    patient = get_object_or_404(Patient, pk=patient_id) if patient_id else None
    form = LabOrderForm(request.POST or None, patient=patient)
    if request.method == "POST" and form.is_valid():
        order = form.save()
        LabOrderTest.objects.create(lab_order=order, test_name=form.cleaned_data["test_name"], result_value=form.cleaned_data.get("result_value", ""), unit=form.cleaned_data.get("unit", ""))
        log_audit(request, "create", "LabOrder", order.pk, str(order))
        messages.success(request, "تم تسجيل طلب المختبر.")
        return redirect("laboratory:list")
    return render(request, "shared/form.html", {"form": form, "title": "طلب مختبر جديد", "submit_label": "حفظ الطلب"})


@roles_required("doctor", "organizer", "data_auditor")
@transaction.atomic
def order_edit(request, pk):
    order = get_object_or_404(
        LabOrder.objects.select_related("requesting_doctor_reference").prefetch_related("tests"), pk=pk
    )
    form = LabOrderForm(request.POST or None, instance=order, patient=order.patient)
    if request.method == "POST" and form.is_valid():
        order = form.save()
        test = order.tests.first() or LabOrderTest(lab_order=order)
        test.test_name = form.cleaned_data["test_name"]
        test.result_value = form.cleaned_data.get("result_value", "")
        test.unit = form.cleaned_data.get("unit", "")
        test.save()
        log_audit(request, "update", "LabOrder", order.pk, str(order))
        messages.success(request, "تم تحديث طلب المختبر وبياناته.")
        return redirect("laboratory:list")
    return render(request, "shared/form.html", {"form": form, "title": "تعديل طلب المختبر", "submit_label": "حفظ التعديلات"})
