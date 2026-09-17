from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.utils import log_audit, roles_required
from apps.patients.models import Patient

from .forms import ReferralForm
from .models import Referral


@login_required
def referral_list(request):
    items = Referral.objects.select_related("patient", "patient__primary_name", "referring_doctor", "referring_doctor_reference")
    if request.GET.get("patient"): items = items.filter(patient_id=request.GET["patient"])
    return render(request, "referrals/list.html", {"page": Paginator(items, 30).get_page(request.GET.get("page"))})


@roles_required("doctor", "organizer")
def referral_create(request, patient_id=None):
    patient = get_object_or_404(Patient, pk=patient_id) if patient_id else None
    form = ReferralForm(request.POST or None, patient=patient)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        log_audit(request, "create", "Referral", item.pk, str(item))
        messages.success(request, "تم إنشاء الإحالة ورمزها الآمن.")
        return redirect("referrals:list")
    return render(request, "shared/form.html", {"form": form, "title": "إحالة جديدة", "submit_label": "حفظ الإحالة"})


@roles_required("doctor", "organizer", "data_auditor")
def referral_edit(request, pk):
    item = get_object_or_404(Referral, pk=pk)
    form = ReferralForm(request.POST or None, instance=item, patient=item.patient)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        log_audit(request, "update", "Referral", item.pk, str(item))
        messages.success(request, "تم تحديث الإحالة وبياناتها.")
        return redirect("referrals:list")
    return render(request, "shared/form.html", {"form": form, "patient": item.patient, "title": "تعديل الإحالة", "submit_label": "حفظ التعديلات"})
