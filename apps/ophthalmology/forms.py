from django import forms
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.core.form_mixins import PatientCodeModelFormMixin

from .models import EyeClinicVisit


class EyeVisitForm(PatientCodeModelFormMixin, forms.ModelForm):
    class Meta:
        model = EyeClinicVisit
        fields = ["visit_date", "doctor", "organizer", "chief_complaint", "diagnosis", "visual_acuity_right", "visual_acuity_left", "iop_right", "iop_left", "notes", "status"]
        widgets = {"visit_date": forms.DateTimeInput(attrs={"type": "datetime-local"}), "chief_complaint": forms.Textarea(attrs={"rows": 2}), "diagnosis": forms.Textarea(attrs={"rows": 2}), "notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = User.objects.filter(role__code=Role.CODE_DOCTOR, is_active=True)
        self.fields["organizer"].queryset = User.objects.filter(role__code=Role.CODE_ORGANIZER, is_active=True)
        self.fields["visit_date"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")
