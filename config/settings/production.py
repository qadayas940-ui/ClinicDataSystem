"""إعدادات بيئة الإنتاج (النسخة التشغيلية عبر Waitress + pywebview)."""
from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

if not SECRET_KEY or SECRET_KEY == "clinic-development-only-secret":
    raise ImproperlyConfigured("يجب إنشاء SECRET_KEY آمن قبل تشغيل نسخة الإنتاج.")

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql" and not config(
    "ALLOW_SQLITE_PRODUCTION", default=False, cast=bool
):
    raise ImproperlyConfigured(
        "نسخة الإنتاج متعددة المستخدمين تتطلب DATABASE_URL لقاعدة PostgreSQL. "
        "يسمح SQLite فقط للاختبار المحلي الصريح عبر ALLOW_SQLITE_PRODUCTION=true."
    )

# في وضع سطح المكتب يعمل الخادم محلياً فقط
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# تقوية الأمان
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="",
    cast=lambda value: [item.strip() for item in value.split(",") if item.strip()],
)
