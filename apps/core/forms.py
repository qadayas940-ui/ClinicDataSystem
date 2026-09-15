from django import forms

from .models import Department, ReferenceValue, ServerSettings


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "department_type", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")


class ServerSettingsForm(forms.ModelForm):
    class Meta:
        model = ServerSettings
        fields = ["allow_network_access", "port"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")

    def clean_port(self):
        port = self.cleaned_data["port"]
        if not 1024 <= port <= 65535:
            raise forms.ValidationError("اختر منفذاً بين 1024 و65535.")
        return port


class ReferenceValueForm(forms.ModelForm):
    aliases_text = forms.CharField(
        label="الأسماء والصيغ البديلة",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="اكتب كل صيغة في سطر مستقل. ستبقى قابلة للبحث دون تكرارها في القائمة.",
    )

    class Meta:
        model = ReferenceValue
        fields = ["category", "canonical_name", "needs_review", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["aliases_text"].initial = "\n".join(self.instance.aliases)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        item = super().save(commit=False)
        item.aliases = [line.strip() for line in self.cleaned_data.get("aliases_text", "").splitlines() if line.strip()]
        if commit:
            item.save()
        return item
