"""وسيط إجبار المستخدم على تغيير كلمة المرور المؤقتة."""
from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """
    إذا كان المستخدم مطالَباً بتغيير كلمة المرور (is_force_password_change)،
    يُعاد توجيهه إلى صفحة تغيير كلمة المرور حتى يغيّرها.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and getattr(user, "is_force_password_change", False):
            allowed = [
                reverse("accounts:change_password"),
                reverse("accounts:logout"),
            ]
            # السماح بالملفات الثابتة وواجهة الإدارة الأساسية
            if request.path not in allowed and not request.path.startswith("/static/"):
                return redirect("accounts:change_password")
        return self.get_response(request)
