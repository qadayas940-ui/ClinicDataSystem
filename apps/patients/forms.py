import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

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
        label="الاسم الرباعي",
        max_length=255,
        help_text="اكتب أربعة أسماء على الأقل. مثال: أحمد محمد علي حسين.",
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
        required=True,
        help_text="يقبل 07899189225 أو +9647899189225 ويحفظه موحداً بصيغة +964.",
    )
    address = forms.CharField(label="منطقة السكن / العنوان", max_length=500, required=True)

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
        if len(units) < 4:
            raise forms.ValidationError("الاسم يجب أن يكون رباعياً على الأقل. الاسم الثنائي أو الثلاثي يحتاج إكمال.")
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
        if not data.get("date_of_birth") and data.get("approx_age_value") is None:
            raise ValidationError("أدخل تاريخ الميلاد، أو أدخل العمر التقريبي إذا كان التاريخ غير معروف.")
        if data.get("approx_age_value") is not None and not data.get("approx_age_unit"):
            self.add_error("approx_age_unit", "اختر وحدة العمر التقريبي.")
        return data

    def apply_widget_classes(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        return self
