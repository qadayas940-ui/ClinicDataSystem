"""إعدادات بيئة الإنتاج (النسخة التشغيلية عبر Waitress + pywebview)."""
from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

if not SECRET_KEY or SECRET_KEY == "clinic-development-only-secret":
    raise ImproperlyConfigured("يجب إنشاء SECRET_KEY آمن قبل تشغيل نسخة الإنتاج.")

# في وضع سطح المكتب يعمل الخادم محلياً فقط
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# تقوية الأمان
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "SAMEORIGIN"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_REFERRER_POLICY = "same-origin"
