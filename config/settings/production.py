"""إعدادات بيئة الإنتاج (النسخة التشغيلية عبر Waitress + pywebview)."""
from .base import *  # noqa: F401,F403

DEBUG = False

# في وضع سطح المكتب يعمل الخادم محلياً فقط
ALLOWED_HOSTS = config(  # noqa: F405
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# تقوية الأمان
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "SAMEORIGIN"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
