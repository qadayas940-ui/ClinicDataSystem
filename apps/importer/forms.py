from django import forms


class WorkbookUploadForm(forms.Form):
    workbook = forms.FileField(label="ملف Excel")

    def clean_workbook(self):
        file = self.cleaned_data["workbook"]
        if not file.name.lower().endswith((".xlsx", ".xlsm")):
            raise forms.ValidationError("النسخة الحالية تقبل ملفات XLSX وXLSM فقط.")
        if file.size > 250 * 1024 * 1024:
            raise forms.ValidationError("حجم الملف يتجاوز 250MB.")
        return file

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workbook"].widget.attrs.update({"class": "form-control", "accept": ".xlsx,.xlsm"})


class ReviewForm(forms.Form):
    decision = forms.ChoiceField(label="القرار", choices=[("accept", "قبول"), ("correct", "تصحيح"), ("reject", "رفض"), ("defer", "تأجيل")])
    corrected_value = forms.CharField(label="القيمة المصححة", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    notes = forms.CharField(label="ملاحظات القرار", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")
