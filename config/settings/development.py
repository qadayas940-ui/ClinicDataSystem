"""إعدادات بيئة التطوير."""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# قبول مضيف المعاينة (preview host) عند التشغيل عبر runserver
INTERNAL_IPS = ["127.0.0.1"]

# تسهيل التطوير: عرض رسائل الأخطاء بالكامل
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
