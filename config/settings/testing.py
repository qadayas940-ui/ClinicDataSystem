"""إعدادات بيئة الاختبار — قاعدة بيانات في الذاكرة وتشفير سريع."""
from .base import *

DEBUG = False

# قاعدة بيانات في الذاكرة لتسريع الاختبارات
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# تشفير أسرع أثناء الاختبار (يبقى آمناً — لا يخزّن نصاً واضحاً)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# تعطيل التقييد الزمني للقفل غير الضروري في الاختبارات المتحكم بها
LOGGING = {"version": 1, "disable_existing_loggers": True}
