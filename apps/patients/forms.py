import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.models import Department, ReferenceValue

from .models import Patient


def normalize_iraqi_mobile(value):
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("964"):
        local = "0" + digits[3:]
    elif digits.startswith("7"):
        local = "0" + digits
    else:
        local = digits
    if not re.fullmatch(r"07[578]\d{8}", local):
        raise ValidationError("رقم الهاتف يجب أن يكون عراقياً صحيحاً من 11 رقم مثل 07899189225 أو +9647899189225.")
    return "+964" + local[1:]


class PatientForm(forms.Form):
    full_name = forms.CharField(
        label="اسم المريض",
        max_length=255,
        help_text="اكتب اسمين على الأقل؛ سيبحث النظام تلقائياً عن السجلات الأقرب.",
    )
    gender = forms.ChoiceField(label="الجنس", choices=Patient.GENDER_CHOICES)
    date_of_birth = forms.DateField(
        label="تاريخ الميلاد",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "data-birthdate": "1"}),
        help_text="يمكن اختياره من التقويم أو كتابته بصيغة سنة-شهر-يوم، وسيظهر العمر تلقائياً.",
    )
    approx_age_value = forms.IntegerField(
        label="العمر التقريبي",
        min_value=0,
        max_value=150,
        required=False,
        help_text="استخدمه فقط إذا كان تاريخ الميلاد غير معروف.",
    )
    approx_age_unit = forms.ChoiceField(
        label="وحدة العمر",
        required=False,
        choices=[("", "— اختر —")] + Patient.AGE_UNIT_CHOICES,
        help_text="تحدد معنى رقم العمر التقريبي: سنة، شهر، أو يوم.",
    )
    phone = forms.CharField(
        label="رقم الهاتف",
        max_length=40,
        required=False,
        help_text="اختياري. يقبل 07899189225 أو +9647899189225 ويحفظه موحداً بصيغة +964.",
    )
    address = forms.CharField(label="منطقة السكن / العنوان", max_length=500, required=False)
    department = forms.ModelChoiceField(label="القسم", queryset=Department.objects.none(), required=False)
    doctor_reference = forms.ModelChoiceField(
        label="اسم الطبيب", queryset=ReferenceValue.objects.none(), required=False,
        empty_label="— اختر القسم أولاً —",
    )
    organizer_reference = forms.ModelChoiceField(
        label="اسم المنظّم", queryset=ReferenceValue.objects.none(), required=False,
        empty_label="— اختر المنظّم —",
    )
    visit_date = forms.DateField(
        label="تاريخ الزيارة", required=False, widget=forms.DateInput(attrs={"type": "date"}),
    )
    visit_time = forms.TimeField(
        label="وقت الزيارة", required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time", "step": "60", "data-visit-time": "1"}),
        help_text="يُحفظ الوقت الفعلي ويُعرض بنظام 12 ساعة AM / PM.",
    )
    diagnosis_reference = forms.ModelChoiceField(
        label="الحالة / التشخيص", queryset=ReferenceValue.objects.none(), required=False,
        empty_label="— اختر الحالة —",
    )
    chief_complaint = forms.CharField(
        label="السبب / الشكوى", max_length=1000, required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    notes = forms.CharField(label="الملاحظات", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    def __init__(self, *args, require_complete=False, department=None, language="ar", **kwargs):
        self.require_complete = require_complete
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.fields["organizer_reference"].queryset = ReferenceValue.objects.filter(category="organizer", is_active=True)
        self.fields["diagnosis_reference"].queryset = ReferenceValue.objects.filter(category="diagnosis", is_active=True)
        selected_department = department
        if self.is_bound:
            selected_department = self.data.get("department") or selected_department
        elif self.initial.get("department"):
            selected_department = self.initial["department"]
        doctors = ReferenceValue.objects.filter(category="doctor", is_active=True)
        if selected_department:
            try:
                doctors = doctors.filter(departments__pk=int(getattr(selected_department, "pk", selected_department)))
            except (TypeError, ValueError):
                doctors = doctors.none()
        else:
            doctors = doctors.none()
        self.fields["doctor_reference"].queryset = doctors.distinct()
        now = timezone.localtime()
        self.fields["visit_date"].initial = self.fields["visit_date"].initial or now.date()
        self.fields["visit_time"].initial = self.fields["visit_time"].initial or now.time().replace(second=0, microsecond=0)
        if require_complete:
            for name in ("department", "doctor_reference", "organizer_reference", "visit_date", "visit_time"):
                self.fields[name].required = True
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["department"].widget.attrs["data-department-select"] = "1"
        self.fields["doctor_reference"].widget.attrs["data-doctor-select"] = "1"
        for name in ("department", "doctor_reference", "organizer_reference", "diagnosis_reference"):
            self.fields[name].widget.attrs["data-searchable-combobox"] = "1"
        self.fields["department"].widget.attrs["data-reference-category"] = "department"
        self.fields["doctor_reference"].widget.attrs["data-reference-category"] = "doctor"
        self.fields["organizer_reference"].widget.attrs["data-reference-category"] = "organizer"
        self.fields["diagnosis_reference"].widget.attrs["data-reference-category"] = "diagnosis"
        self.fields["full_name"].widget.attrs["data-patient-match-name"] = "1"
        self.fields["phone"].widget.attrs["data-patient-match-phone"] = "1"
        self.fields["approx_age_value"].widget.attrs["data-patient-match-age"] = "1"
        if str(language).startswith("en"):
            labels = {
                "full_name": "Full name", "gender": "Gender", "date_of_birth": "Date of birth",
                "approx_age_value": "Approximate age", "approx_age_unit": "Age unit",
                "phone": "Phone number", "address": "Area / address", "department": "Department",
                "doctor_reference": "Doctor", "organizer_reference": "Organizer", "visit_date": "Visit date", "visit_time": "Visit time",
                "diagnosis_reference": "Status / diagnosis", "chief_complaint": "Reason / complaint",
                "notes": "Notes",
            }
            for name, label in labels.items():
                self.fields[name].label = label
            self.fields["gender"].choices = [("male", "Male"), ("female", "Female"), ("unknown", "Unknown")]
            self.fields["approx_age_unit"].choices = [("", "— Select —"), ("year", "Year"), ("month", "Month"), ("day", "Day")]

    def clean_full_name(self):
        value = re.sub(r"\s+", " ", self.cleaned_data["full_name"]).strip()
        parts = value.split(" ")
        units = []
        index = 0
        compound_starts = {"عبد", "ابو", "أبو", "ام", "أم"}
        while index < len(parts):
            if parts[index] in compound_starts and index + 1 < len(parts):
                units.append(parts[index] + " " + parts[index + 1])
                index += 2
            else:
                units.append(parts[index])
                index += 1
        if self.require_complete and len(units) < 2:
            raise forms.ValidationError("اكتب اسمين على الأقل للبحث والتسجيل.")
        if re.search(r"[0-9٠-٩]", value):
            raise forms.ValidationError("الاسم لا يجب أن يحتوي أرقاماً.")
        return value

    def clean_phone(self):
        return normalize_iraqi_mobile(self.cleaned_data.get("phone"))

    def clean(self):
        data = super().clean()
        if data.get("date_of_birth") and data["date_of_birth"].year < 1900:
            self.add_error("date_of_birth", "تاريخ الميلاد قديم بصورة غير منطقية.")
        if data.get("date_of_birth") and data["date_of_birth"] > timezone.localdate():
            self.add_error("date_of_birth", "تاريخ الميلاد لا يمكن أن يكون في المستقبل.")
        if data.get("date_of_birth") and data.get("approx_age_value") is not None:
            raise ValidationError("اختر تاريخ الميلاد أو العمر التقريبي، وليس الاثنين معاً.")
        if self.require_complete and not data.get("date_of_birth") and data.get("approx_age_value") is None:
            raise ValidationError("أدخل تاريخ الميلاد، أو أدخل العمر التقريبي إذا كان التاريخ غير معروف.")
        if data.get("approx_age_value") is not None and not data.get("approx_age_unit"):
            self.add_error("approx_age_unit", "اختر وحدة العمر التقريبي.")
        return data

    def apply_widget_classes(self):
        return self
