import uuid

from django import forms
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.core.models import ReferenceValue
from apps.core.form_mixins import PatientCodeModelFormMixin

from .models import Referral


class ReferralForm(PatientCodeModelFormMixin, forms.ModelForm):
    class Meta:
        model = Referral
        fields = ["referring_doctor_reference", "destination_name", "destination_type", "reason", "referral_date", "status", "followup_notes"]
        widgets = {"referral_date": forms.DateTimeInput(attrs={"type": "datetime-local"}), "reason": forms.Textarea(attrs={"rows": 2}), "followup_notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["referring_doctor_reference"].queryset = ReferenceValue.objects.filter(category="doctor", is_active=True)
        self.fields["referring_doctor_reference"].widget.attrs.update({"data-searchable-combobox": "1", "data-reference-category": "doctor"})
        self.fields["destination_name"].widget.attrs.update({"data-reference-text": "1", "data-reference-category": "referral_destination"})
        if not self.instance.pk:
            self.fields["referral_date"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        referral = super().save(commit=False)
        if not referral.qr_code_data:
            referral.qr_code_data = f"REF-{uuid.uuid4().hex}"
        if commit: referral.save()
        return referral
