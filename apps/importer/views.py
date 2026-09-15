from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.utils import log_audit, roles_required

from .forms import ReviewForm, WorkbookUploadForm
from .models import ImportBatch, ReviewDecision, SourceRow
from .services import analyze_workbook, archive_upload


@login_required
def batch_list(request):
    batches = ImportBatch.objects.prefetch_related("sheets")
    return render(request, "importer/batch_list.html", {"batches": batches})


@roles_required("data_auditor")
def upload_workbook(request):
    form = WorkbookUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        uploaded = form.cleaned_data["workbook"]
        file_path, digest = archive_upload(uploaded)
        batch, created = analyze_workbook(file_path, digest, uploaded.name, request.user)
        if created:
            log_audit(request, "import", "ImportBatch", batch.pk, uploaded.name)
            messages.success(request, f"اكتمل فحص {batch.total_rows:,} سجل. لم يُدمج أو يُحذف أي مريض تلقائياً.")
        else:
            messages.warning(request, "هذه النسخة مطابقة تماماً لملف سبق تحليله؛ مُنع الاستيراد المكرر.")
        return redirect("importer:batch_detail", pk=batch.pk)
    return render(request, "importer/upload.html", {"form": form})


@login_required
def batch_detail(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk)
    selected = request.GET.get("classification", "")
    rows = batch.rows.select_related("sheet").prefetch_related("issues")
    if selected:
        rows = rows.filter(classification=selected)
    page = Paginator(rows, 50).get_page(request.GET.get("page"))
    counts = {key: batch.rows.filter(classification=key).count() for key, _ in SourceRow.CLASSIFICATION_CHOICES}
    return render(request, "importer/batch_detail.html", {"batch": batch, "page": page, "counts": counts, "selected": selected})


@login_required
def row_detail(request, pk):
    row = get_object_or_404(SourceRow.objects.select_related("batch", "sheet"), pk=pk)
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ReviewDecision.objects.create(source_row=row, field_name="__record__", original_value="", corrected_value=form.cleaned_data.get("corrected_value", ""), decision=form.cleaned_data["decision"], decided_by=request.user, notes=form.cleaned_data.get("notes", ""))
        decision = form.cleaned_data["decision"]
        row.status = "accepted" if decision in {"accept", "correct"} else ("rejected" if decision == "reject" else "reviewed")
        row.save(update_fields=["status"])
        log_audit(request, "update", "SourceRow", row.pk, f"review:{decision}")
        messages.success(request, "تم حفظ قرار المراجعة دون تغيير السجل الأصلي.")
        return redirect("importer:batch_detail", pk=row.batch_id)
    return render(request, "importer/row_detail.html", {"row": row, "form": form})
