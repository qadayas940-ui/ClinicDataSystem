from django import forms


class PatientCodeModelFormMixin:
    """اختيار المريض برمزه بدلاً من تحميل عشرات آلاف المرضى في قائمة."""

    patient_code = forms.CharField(label="الرقم التعريفي للمريض", max_length=40, help_text="مثال: CLN-AB12CD34EF")

    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        if "patient_code" not in self.fields:
            self.fields["patient_code"] = forms.CharField(
                label="الرقم التعريفي للمريض", max_length=40,
                help_text="مثال: CLN26-0000000001",
            )
        if patient:
            self.resolved_patient = patient
            self.fields["patient_code"].initial = patient.internal_code
            self.fields["patient_code"].widget = forms.HiddenInput()
        elif getattr(self.instance, "patient_id", None):
            self.fields["patient_code"].initial = self.instance.patient.internal_code

    def clean_patient_code(self):
        from apps.patients.models import Patient

        code = self.cleaned_data["patient_code"].strip().upper()
        if getattr(self, "resolved_patient", None) and self.resolved_patient.internal_code.upper() == code:
            return code
        try:
            self.resolved_patient = Patient.objects.get(internal_code__iexact=code)
        except Patient.DoesNotExist as exc:
            raise forms.ValidationError("لا يوجد مريض بهذا الرقم. ابحث عن المريض أو أنشئ ملفاً أولاً.") from exc
        return code

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.patient = self.resolved_patient
        if commit:
            instance.save()
            self.save_m2m()
        return instance
