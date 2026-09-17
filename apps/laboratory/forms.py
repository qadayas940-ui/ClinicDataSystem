from django import forms
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.core.form_mixins import PatientCodeModelFormMixin

from .models import LabOrder


class LabOrderForm(PatientCodeModelFormMixin, forms.ModelForm):
    test_name = forms.CharField(label="اسم الفحص", max_length=200)
    result_value = forms.CharField(label="النتيجة", max_length=120, required=False)
    unit = forms.CharField(label="الوحدة", max_length=40, required=False)

    class Meta:
        model = LabOrder
        fields = ["order_date", "requesting_doctor", "status", "result_date", "notes"]
        widgets = {"order_date": forms.DateTimeInput(attrs={"type": "datetime-local"}), "result_date": forms.DateTimeInput(attrs={"type": "datetime-local"}), "notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requesting_doctor"].queryset = User.objects.filter(role__code=Role.CODE_DOCTOR, is_active=True)
        if not self.instance.pk:
            self.fields["order_date"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        elif not self.is_bound:
            test = self.instance.tests.first()
            if test:
                self.fields["test_name"].initial = test.test_name
                self.fields["result_value"].initial = test.result_value
                self.fields["unit"].initial = test.unit
        self.fields["test_name"].widget.attrs.update({"data-reference-text": "1", "data-reference-category": "lab_test"})
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")
