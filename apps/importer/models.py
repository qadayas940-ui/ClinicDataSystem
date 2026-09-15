"""نماذج الاستيراد (المرحلة 4 — النماذج فقط الآن)."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class ImportBatch(SoftDeleteModel):
    """دفعة استيراد من ملف."""

    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("processing", "قيد المعالجة"),
        ("reviewing", "قيد المراجعة"),
        ("completed", "مكتملة"),
        ("failed", "فاشلة"),
    ]

    file_hash = models.CharField("بصمة الملف (SHA-256)", max_length=64, db_index=True)
    original_filename = models.CharField("اسم الملف الأصلي", max_length=255)
    file_size = models.BigIntegerField("حجم الملف", default=0)
    import_type = models.CharField("نوع الاستيراد", max_length=80, blank=True, default="")
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="pending")
    total_rows = models.PositiveIntegerField("إجمالي الصفوف", default=0)
    valid_rows = models.PositiveIntegerField("الصفوف الصالحة", default=0)
    issue_rows = models.PositiveIntegerField("صفوف بها مشاكل", default=0)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="استوردها", on_delete=models.SET_NULL, null=True, blank=True, related_name="import_batches")
    completed_at = models.DateTimeField("اكتملت في", null=True, blank=True)
    notes = models.TextField("ملاحظات", blank=True, default="")
    previous_batch = models.ForeignKey(
        "self", verbose_name="الدفعة السابقة", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="newer_batches",
    )

    class Meta:
        verbose_name = "دفعة استيراد"
        verbose_name_plural = "دفعات الاستيراد"
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_filename


class ImportFile(models.Model):
    """ملف مرتبط بدفعة استيراد."""

    batch = models.ForeignKey(ImportBatch, verbose_name="الدفعة", on_delete=models.CASCADE, related_name="files")
    file_path = models.CharField("مسار الملف", max_length=500)
    file_hash = models.CharField("بصمة الملف", max_length=64)

    class Meta:
        verbose_name = "ملف استيراد"
        verbose_name_plural = "ملفات الاستيراد"

    def __str__(self):
        return self.file_path


class ImportSheet(models.Model):
    """ورقة (Sheet) داخل ملف الاستيراد."""

    batch = models.ForeignKey(ImportBatch, verbose_name="الدفعة", on_delete=models.CASCADE, related_name="sheets")
    sheet_name = models.CharField("اسم الورقة", max_length=200)
    sheet_index = models.PositiveIntegerField("ترتيب الورقة", default=0)
    header_row = models.PositiveIntegerField("صف العناوين", default=1)
    first_data_row = models.PositiveIntegerField("أول صف بيانات", default=2)
    total_rows = models.PositiveIntegerField("إجمالي الصفوف", default=0)
    actual_data_rows = models.PositiveIntegerField("صفوف البيانات الفعلية", default=0)
    column_mapping = models.JSONField("خريطة الأعمدة", default=dict, blank=True)
    notes = models.TextField("ملاحظات", blank=True, default="")

    class Meta:
        verbose_name = "ورقة استيراد"
        verbose_name_plural = "أوراق الاستيراد"
        ordering = ["sheet_index"]

    def __str__(self):
        return self.sheet_name


class SourceRow(models.Model):
    """صف مصدري من ملف الاستيراد."""

    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("reviewed", "تمت مراجعته"),
        ("accepted", "مقبول"),
        ("rejected", "مرفوض"),
    ]
    CLASSIFICATION_CHOICES = [
        ("ready", "جاهز للاستيراد"),
        ("review", "يحتاج مراجعة"),
        ("blocking", "خطأ مانع"),
        ("duplicate", "تكرار محتمل"),
        ("repeat_visit", "زيارة متكررة محتملة"),
    ]

    batch = models.ForeignKey(ImportBatch, verbose_name="الدفعة", on_delete=models.CASCADE, related_name="rows")
    sheet = models.ForeignKey(ImportSheet, verbose_name="الورقة", on_delete=models.CASCADE, related_name="rows")
    original_row_number = models.PositiveIntegerField("رقم الصف الأصلي")
    raw_data = models.JSONField("البيانات الخام", default=dict)
    row_hash = models.CharField("بصمة الصف", max_length=64, db_index=True)
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="pending")
    issues_count = models.PositiveIntegerField("عدد المشاكل", default=0)
    classification = models.CharField("التصنيف", max_length=20, choices=CLASSIFICATION_CHOICES, default="ready", db_index=True)
    flag_reasons = models.JSONField("أسباب الإشارة", default=list, blank=True)
    normalized_name = models.CharField("الاسم المطبّع", max_length=255, blank=True, default="", db_index=True)
    linked_patient = models.ForeignKey(
        "patients.Patient", verbose_name="المريض المرتبط", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="source_rows",
    )

    class Meta:
        verbose_name = "صف مصدري"
        verbose_name_plural = "الصفوف المصدرية"
        ordering = ["original_row_number"]
        constraints = [
            models.UniqueConstraint(fields=["batch", "sheet", "original_row_number"], name="uniq_source_row_location"),
        ]

    def __str__(self):
        return f"صف {self.original_row_number}"


class DataIssue(models.Model):
    """مشكلة في بيانات صف مصدري."""

    ISSUE_TYPE_CHOICES = [
        ("error", "خطأ"),
        ("warning", "تحذير"),
        ("info", "معلومة"),
    ]
    SEVERITY_CHOICES = [
        ("blocking", "مانع"),
        ("warning", "تحذير"),
        ("info", "معلومة"),
    ]

    source_row = models.ForeignKey(SourceRow, verbose_name="الصف المصدري", on_delete=models.CASCADE, related_name="issues")
    field_name = models.CharField("اسم الحقل", max_length=120)
    original_value = models.TextField("القيمة الأصلية", blank=True, default="")
    issue_type = models.CharField("نوع المشكلة", max_length=20, choices=ISSUE_TYPE_CHOICES, default="warning")
    severity = models.CharField("الخطورة", max_length=20, choices=SEVERITY_CHOICES, default="warning")
    description = models.TextField("الوصف", blank=True, default="")
    is_auto_fixable = models.BooleanField("قابل للإصلاح التلقائي", default=False)
    suggested_value = models.TextField("القيمة المقترحة", blank=True, default="")

    class Meta:
        verbose_name = "مشكلة بيانات"
        verbose_name_plural = "مشاكل البيانات"

    def __str__(self):
        return f"{self.field_name}: {self.get_issue_type_display()}"


class ReviewDecision(models.Model):
    """قرار مراجعة لحقل في صف مصدري."""

    DECISION_CHOICES = [
        ("accept", "قبول"),
        ("reject", "رفض"),
        ("correct", "تصحيح"),
        ("defer", "تأجيل"),
    ]

    source_row = models.ForeignKey(SourceRow, verbose_name="الصف المصدري", on_delete=models.CASCADE, related_name="decisions")
    field_name = models.CharField("اسم الحقل", max_length=120)
    original_value = models.TextField("القيمة الأصلية", blank=True, default="")
    corrected_value = models.TextField("القيمة المصححة", blank=True, default="")
    decision = models.CharField("القرار", max_length=20, choices=DECISION_CHOICES, default="accept")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="قرّرها", on_delete=models.SET_NULL, null=True, blank=True, related_name="review_decisions")
    decided_at = models.DateTimeField("تاريخ القرار", auto_now_add=True)
    notes = models.CharField("ملاحظات", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "قرار مراجعة"
        verbose_name_plural = "قرارات المراجعة"

    def __str__(self):
        return f"{self.field_name}: {self.get_decision_display()}"


class MatchCandidate(models.Model):
    """مرشّح تطابق بين صفّين مصدريين (للكشف عن التكرار)."""

    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("confirmed", "مؤكد"),
        ("rejected", "مرفوض"),
    ]

    source_row_a = models.ForeignKey(SourceRow, verbose_name="الصف أ", on_delete=models.CASCADE, related_name="match_candidates_a")
    source_row_b = models.ForeignKey(SourceRow, verbose_name="الصف ب", on_delete=models.CASCADE, related_name="match_candidates_b")
    match_score = models.FloatField("درجة التطابق", default=0.0)
    match_reason = models.CharField("سبب التطابق", max_length=255, blank=True, default="")
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="راجعها", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_matches")
    reviewed_at = models.DateTimeField("تاريخ المراجعة", null=True, blank=True)
    notes = models.CharField("ملاحظات", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "مرشّح تطابق"
        verbose_name_plural = "مرشّحو التطابق"

    def __str__(self):
        return f"تطابق {self.match_score:.2f}"


class MergeDecision(models.Model):
    """قرار دمج بين مرشّحي تطابق."""

    DECISION_CHOICES = [
        ("merge", "دمج"),
        ("keep_separate", "إبقاء منفصل"),
        ("defer", "تأجيل"),
    ]

    candidates = models.ManyToManyField(MatchCandidate, verbose_name="المرشّحون", related_name="merge_decisions", blank=True)
    decision = models.CharField("القرار", max_length=20, choices=DECISION_CHOICES, default="defer")
    merged_patient = models.ForeignKey("patients.Patient", verbose_name="المريض المدموج", on_delete=models.SET_NULL, null=True, blank=True, related_name="merge_decisions")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="قرّرها", on_delete=models.SET_NULL, null=True, blank=True, related_name="merge_decisions")
    decided_at = models.DateTimeField("تاريخ القرار", auto_now_add=True)
    notes = models.CharField("ملاحظات", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "قرار دمج"
        verbose_name_plural = "قرارات الدمج"

    def __str__(self):
        return f"{self.get_decision_display()} @ {self.decided_at}"
