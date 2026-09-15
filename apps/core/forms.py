from django import forms

from .models import Department, ServerSettings


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
