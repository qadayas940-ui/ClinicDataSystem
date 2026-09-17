"""نماذج (Forms) تطبيق الحسابات."""
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password

from .models import Role, User


class ArabicLoginForm(forms.Form):
    """نموذج تسجيل الدخول العربي."""

    username = forms.CharField(
        label="اسم المستخدم",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control form-control-lg", "placeholder": "اسم المستخدم", "autofocus": True, "dir": "ltr"}),
    )
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={"class": "form-control form-control-lg", "placeholder": "كلمة المرور", "dir": "ltr"}),
    )


class OwnerSetupForm(forms.Form):
    """نموذج إنشاء حساب المالك الأول."""

    full_name = forms.CharField(
        label="الاسم الكامل",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control form-control-lg", "placeholder": "الاسم الكامل"}),
    )
    username = forms.CharField(
        label="اسم المستخدم",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control form-control-lg", "placeholder": "اسم المستخدم", "dir": "ltr"}),
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control form-control-lg", "placeholder": "name@example.com", "dir": "ltr"}),
    )
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={"class": "form-control form-control-lg", "dir": "ltr"}),
    )
    password_confirm = forms.CharField(
        label="تأكيد كلمة المرور",
        widget=forms.PasswordInput(attrs={"class": "form-control form-control-lg", "dir": "ltr"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("اسم المستخدم مستخدم من قبل. اختر اسماً آخر.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        pwd = cleaned.get("password")
        confirm = cleaned.get("password_confirm")
        if pwd and confirm and pwd != confirm:
            self.add_error("password_confirm", "كلمتا المرور غير متطابقتين.")
        return cleaned

    def save(self):
        """إنشاء حساب المالك مع الدور المناسب. كلمة المرور تُخزَّن مُجزّأة."""
        data = self.cleaned_data
        owner_role, _ = Role.objects.get_or_create(
            code=Role.CODE_OWNER,
            defaults={"name": "المالك", "is_system_role": True, "description": "مالك النظام بكامل الصلاحيات"},
        )
        first_name = data["full_name"].split(" ")[0]
        last_name = " ".join(data["full_name"].split(" ")[1:])
        user = User(
            username=data["username"],
            email=data.get("email", ""),
            first_name=first_name,
            last_name=last_name,
            role=owner_role,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            is_force_password_change=False,
        )
        user.set_password(data["password"])  # تجزئة كلمة المرور
        user.save()
        return user


class ArabicPasswordChangeForm(PasswordChangeForm):
    """نموذج تغيير كلمة المرور بعناوين عربية."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "كلمة المرور الحالية"
        self.fields["new_password1"].label = "كلمة المرور الجديدة"
        self.fields["new_password2"].label = "تأكيد كلمة المرور الجديدة"
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control form-control-lg", "dir": "ltr"})


class StaffUserForm(forms.ModelForm):
    password = forms.CharField(label="كلمة المرور المؤقتة", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "department", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.exclude(code=Role.CODE_OWNER)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        if not self.instance.pk:
            self.fields["password"].required = True

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
            user.is_force_password_change = True
        if commit:
            user.save()
        return user


class AccountProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "الاسم الأول", "last_name": "بقية الاسم", "email": "البريد الإلكتروني"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
