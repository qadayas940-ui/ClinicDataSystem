from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.utils import log_audit, roles_required
from apps.patients.models import Patient

from .forms import VisitForm
from .models import Visit


@login_required
def visit_list(request):
    visits = Visit.objects.select_related("patient", "patient__primary_name", "doctor", "department")
    if request.GET.get("patient"):
        visits = visits.filter(patient_id=request.GET["patient"])
    page = Paginator(visits, 30).get_page(request.GET.get("page"))
    return render(request, "visits/list.html", {"page": page})


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
        messages.success(request, "تم تسجيل الزيارة وربطها بملف المريض.")
        return redirect("patients:detail", pk=visit.patient_id)
    return render(request, "shared/form.html", {"form": form, "title": "تسجيل زيارة", "submit_label": "حفظ الزيارة"})
