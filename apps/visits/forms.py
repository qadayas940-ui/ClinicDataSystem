from django import forms
from django.utils import timezone

from apps.core.form_mixins import PatientCodeModelFormMixin
from apps.core.models import ReferenceValue

from .models import Visit


class VisitForm(PatientCodeModelFormMixin, forms.ModelForm):
    class Meta:
        model = Visit
        fields = ["visit_date", "visit_type", "department", "doctor_reference", "organizer_reference", "status", "chief_complaint", "diagnosis", "notes"]
        widgets = {"visit_date": forms.DateTimeInput(attrs={"type": "datetime-local"}), "chief_complaint": forms.Textarea(attrs={"rows": 2}), "diagnosis": forms.Textarea(attrs={"rows": 2}), "notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        department = self.data.get("department") if self.is_bound else getattr(self.instance, "department_id", None)
        doctors = ReferenceValue.objects.filter(category="doctor", is_active=True)
        self.fields["doctor_reference"].queryset = doctors.filter(departments__pk=department).distinct() if department else doctors.none()
        self.fields["organizer_reference"].queryset = ReferenceValue.objects.filter(category="organizer", is_active=True)
        self.fields["department"].widget.attrs["data-department-select"] = "1"
        self.fields["doctor_reference"].widget.attrs["data-doctor-select"] = "1"
        for name in ("visit_type", "department", "doctor_reference", "organizer_reference", "status"):
            self.fields[name].widget.attrs["data-searchable-combobox"] = "1"
        self.fields["visit_date"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
