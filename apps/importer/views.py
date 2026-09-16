from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.utils import log_audit, roles_required

from .forms import ReviewForm, WorkbookUploadForm
from .models import ImportBatch, ImportSheet, ReviewDecision, SourceRow
from .services import HEADER_ALIASES, analyze_workbook, archive_upload, import_batch_records, remap_sheet


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
        batch, created = analyze_workbook(file_path, digest, uploaded.name, request.user, form.cleaned_data["import_type"])
        if created:
            log_audit(request, "import", "ImportBatch", batch.pk, uploaded.name)
            messages.success(request, f"اكتمل فحص {batch.total_rows:,} سجل. لم يُدمج أو يُحذف أي مريض تلقائياً.")
        else:
            messages.warning(request, "هذه النسخة مطابقة تماماً لملف سبق تحليله؛ مُنع الاستيراد المكرر.")
        return redirect("importer:batch_detail", pk=batch.pk)
    return render(request, "importer/upload.html", {"form": form})


@roles_required("data_auditor")
def sheet_mapping(request, pk):
    sheet = get_object_or_404(ImportSheet.objects.select_related("batch"), pk=pk)
    sample = sheet.rows.order_by("original_row_number").first()
    headers = list((sample.raw_data.get("source", {}) if sample else {}).keys())
    fields = [("", "بيانات إضافية — لا تُفقد")] + [
        (key, {
            "sequence": "تسلسل", "name": "الاسم", "gender": "الجنس", "age": "العمر",
            "birth_date": "تاريخ الميلاد", "phone": "الهاتف", "address": "العنوان",
            "department": "القسم", "doctor": "الطبيب", "organizer": "المنظم",
            "date": "التاريخ", "status": "الحالة / التشخيص", "notes": "الملاحظات",
            "repeat_count": "عدد التكرار", "destination": "جهة الإحالة", "test": "الفحص",
            "result": "النتيجة", "diagnosis": "التشخيص", "external_id": "المعرف الخارجي",
        }.get(key, key))
        for key in HEADER_ALIASES
    ]
    if request.method == "POST":
        mapping = {header: request.POST.get(f"map_{index}", "") for index, header in enumerate(headers)}
        remap_sheet(sheet, mapping)
        messages.success(request, "تم حفظ خريطة الأعمدة وإعادة فحص الصفوف دون فقد الأعمدة الإضافية.")
        return redirect("importer:batch_detail", pk=sheet.batch_id)
    rows = [{"index": index, "header": header, "selected": sheet.column_mapping.get(header, "")} for index, header in enumerate(headers)]
    return render(request, "importer/sheet_mapping.html", {"sheet": sheet, "rows": rows, "fields": fields})


@roles_required("data_auditor")
def commit_batch(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk)
    if request.method == "POST":
        imported = import_batch_records(batch, request.user)
        log_audit(request, "import", "ImportBatch", batch.pk, f"commit:{imported}")
        messages.success(request, f"تم إدراج {imported:,} سجل قابل للاستيراد. بقيت سجلات المراجعة والمانع دون تغيير.")
        if imported:
            return redirect(f"{reverse('patients:list')}?import_batch={batch.pk}")
    return redirect("importer:batch_detail", pk=batch.pk)


@roles_required("data_auditor")
def commit_row(request, pk):
    row = get_object_or_404(SourceRow.objects.select_related("batch", "sheet"), pk=pk)
    if request.method == "POST":
        if row.classification != "ready" and row.status != "accepted":
            messages.warning(request, "راجع السجل واعتمده أولاً؛ لا يمكن إدراج سجل تحذير أو تكرار تلقائياً.")
            return redirect("importer:row_detail", pk=row.pk)
        imported = import_batch_records(row.batch, request.user, source_row=row)
        if imported:
            messages.success(request, "تمت إضافة السجل وربطه بمريض داخل النظام.")
        else:
            messages.warning(request, "السجل مضاف سابقاً أو غير صالح للإدراج.")
    return redirect("importer:batch_detail", pk=row.batch_id)


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
    sibling_ids = list(row.batch.rows.order_by("sheet_id", "original_row_number").values_list("pk", flat=True))
    index = sibling_ids.index(row.pk)
    canonical = row.raw_data.get("canonical", {})
    from .services import GENDERS, normalize_arabic
    return render(request, "importer/row_detail.html", {
        "row": row,
        "form": form,
        "canonical": canonical,
        "canonical_gender": GENDERS.get(normalize_arabic(canonical.get("gender")), "unknown"),
        "previous_id": sibling_ids[index - 1] if index > 0 else None,
        "next_id": sibling_ids[index + 1] if index + 1 < len(sibling_ids) else None,
    })
