from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.models import Notification
from apps.core.utils import log_audit, roles_required
from apps.patients.models import Patient

from .forms import VisitForm
from .models import Visit


@login_required
def visit_list(request):
    visits = Visit.objects.select_related(
        "patient", "patient__primary_name", "doctor", "department", "doctor_reference", "organizer_reference"
    ).prefetch_related("patient__visits")
    if request.GET.get("patient"):
        visits = visits.filter(patient_id=request.GET["patient"])
    page = Paginator(visits, 30).get_page(request.GET.get("page"))
    return render(request, "visits/list.html", {"page": page})


@roles_required("doctor", "organizer", "data_auditor")
def visit_edit(request, pk):
    visit = get_object_or_404(Visit.objects.select_related("patient"), pk=pk)
    form = VisitForm(request.POST or None, instance=visit, patient=visit.patient)
    if request.method == "POST" and form.is_valid():
        visit = form.save()
        log_audit(request, "update", "Visit", visit.pk, str(visit))
        messages.success(request, "تم تحديث المراجعة مع بقائها مرتبطة بملف المريض.")
        return redirect(f"{reverse('visits:list')}?patient={visit.patient_id}")
    return render(request, "shared/form.html", {
        "form": form, "patient": visit.patient,
        "title": f"تعديل مراجعة {visit.patient.internal_code}", "submit_label": "حفظ التعديلات",
    })


@roles_required("doctor", "organizer")
def visit_create(request, patient_id=None):
    patient = get_object_or_404(Patient, pk=patient_id) if patient_id else None
    form = VisitForm(request.POST or None, patient=patient)
    if request.method == "POST" and form.is_valid():
        visit = form.save(commit=False)
        visit.created_by = request.user
        if request.user.is_organizer:
            visit.organizer = request.user
        visit.save()
        log_audit(request, "create", "Visit", visit.pk, str(visit))
        Notification.objects.create(
            user=request.user, event_type="visit_created", title="تم تسجيل زيارة جديدة",
            message=visit.patient.internal_code, object_type="Visit", object_id=str(visit.pk),
            target_url=reverse("patients:list") + f"?patient={visit.patient_id}",
        )
        messages.success(request, "تم تسجيل الزيارة وربطها بملف المريض.")
        return redirect("patients:detail", pk=visit.patient_id)
    return render(request, "shared/form.html", {"form": form, "patient": patient, "title": "تسجيل زيارة", "submit_label": "حفظ الزيارة"})


@roles_required("data_auditor")
@require_POST
def archive(request, pk):
    item = get_object_or_404(Visit, pk=pk)
    item.soft_delete()
    log_audit(request, "delete", "Visit", item.pk, str(item))
    messages.success(request, "الزيارة نُقل إلى سلة المحذوفات.")
    return redirect("visits:list")


@roles_required("data_auditor")
@require_POST
def restore(request, pk):
    item = get_object_or_404(Visit.all_objects, pk=pk, deleted_at__isnull=False)
    item.restore()
    log_audit(request, "restore", "Visit", item.pk, str(item))
    messages.success(request, "تمت استعادة السجل.")
    return redirect("patients:trash")
