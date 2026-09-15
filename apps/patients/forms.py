from django import forms
from django.core.exceptions import ValidationError

from .models import Patient


class PatientForm(forms.Form):
    full_name = forms.CharField(label="الاسم الرباعي", max_length=255)
    gender = forms.ChoiceField(label="الجنس", choices=Patient.GENDER_CHOICES)
    date_of_birth = forms.DateField(label="تاريخ الميلاد", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    approx_age_value = forms.IntegerField(label="العمر التقريبي", min_value=0, max_value=150, required=False)
    approx_age_unit = forms.ChoiceField(label="وحدة العمر", required=False, choices=[("", "— اختر —")] + Patient.AGE_UNIT_CHOICES)
    phone = forms.CharField(label="رقم الهاتف", max_length=40, required=False)
    address = forms.CharField(label="منطقة السكن / العنوان", max_length=500, required=False)

    def clean(self):
        data = super().clean()
        if data.get("date_of_birth") and data["date_of_birth"].year < 1900:
            self.add_error("date_of_birth", "تاريخ الميلاد قديم بصورة غير منطقية.")
        if data.get("date_of_birth") and data.get("approx_age_value") is not None:
            raise ValidationError("اختر تاريخ الميلاد أو العمر التقريبي، وليس الاثنين معاً.")
        if data.get("approx_age_value") is not None and not data.get("approx_age_unit"):
            self.add_error("approx_age_unit", "اختر وحدة العمر التقريبي.")
        return data

    def apply_widget_classes(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        return self
