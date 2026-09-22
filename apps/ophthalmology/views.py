from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.utils import log_audit, roles_required
from apps.patients.models import Patient

from .forms import EyeVisitForm
from .models import EyeClinicVisit


@login_required
def eye_visit_list(request):
    items = EyeClinicVisit.objects.select_related("patient", "patient__primary_name", "doctor", "organizer")
    if request.GET.get("patient"): items = items.filter(patient_id=request.GET["patient"])
    return render(request, "ophthalmology/list.html", {"page": Paginator(items, 30).get_page(request.GET.get("page"))})


@roles_required("doctor", "organizer")
def eye_visit_create(request, patient_id=None):
    patient = get_object_or_404(Patient, pk=patient_id) if patient_id else None
    form = EyeVisitForm(request.POST or None, patient=patient)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        log_audit(request, "create", "EyeClinicVisit", item.pk, str(item))
        messages.success(request, "تم تسجيل زيارة عيادة العيون.")
        return redirect("ophthalmology:list")
    return render(request, "shared/form.html", {"form": form, "title": "زيارة عيون جديدة", "submit_label": "حفظ الزيارة"})


@roles_required("data_auditor")
@require_POST
def archive(request, pk):
    item = get_object_or_404(EyeClinicVisit, pk=pk)
    item.soft_delete()
    log_audit(request, "delete", "EyeClinicVisit", item.pk, str(item))
    messages.success(request, "زيارة العيون نُقلت إلى سلة المحذوفات.")
    return redirect("ophthalmology:list")


@roles_required("data_auditor")
@require_POST
def restore(request, pk):
    item = get_object_or_404(EyeClinicVisit.all_objects, pk=pk, deleted_at__isnull=False)
    item.restore()
    log_audit(request, "restore", "EyeClinicVisit", item.pk, str(item))
    messages.success(request, "تمت استعادة السجل.")
    return redirect("patients:trash")
