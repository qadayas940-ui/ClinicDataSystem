"""
خلفية مصادقة مخصصة تدعم قفل الحساب بعد محاولات فاشلة.

لا تُسجَّل أي كلمات مرور أو بيانات حساسة في السجلات.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger("clinic")

UserModel = get_user_model()


class LockoutModelBackend(ModelBackend):
    """
    خلفية مصادقة تطبّق سياسة القفل:
    - بعد MAX_LOGIN_ATTEMPTS محاولة فاشلة يُقفل الحساب LOGIN_LOCKOUT_MINUTES دقيقة.
    - عند النجاح يُصفَّر العدّاد.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            user = UserModel.objects.get(**{UserModel.USERNAME_FIELD: username})
        except UserModel.DoesNotExist:
            # تشغيل خوارزمية التجزئة لمنع هجوم توقيت التعداد
            UserModel().set_password(password)
            return None

        # الحساب مقفل حالياً
        if user.is_locked:
            logger.info("محاولة دخول لحساب مقفل: user_id=%s", user.pk)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            # نجاح: تصفير العدّاد
            if user.failed_login_attempts or user.locked_until:
                user.reset_failed_attempts()
            return user

        # فشل: زيادة العدّاد وربما القفل
        user.failed_login_attempts += 1
        max_attempts = getattr(settings, "MAX_LOGIN_ATTEMPTS", 5)
        lockout_minutes = getattr(settings, "LOGIN_LOCKOUT_MINUTES", 10)
        if user.failed_login_attempts >= max_attempts:
            user.lock_account(lockout_minutes)
            logger.info("تم قفل الحساب بعد محاولات فاشلة: user_id=%s", user.pk)
        else:
            user.save(update_fields=["failed_login_attempts"])
        return None
