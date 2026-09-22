"""
الإعدادات الأساسية المشتركة لمشروع ClinicDataSystem.

هذه الإعدادات تُستخدم في جميع البيئات (تطوير/اختبار/إنتاج) ويتم استيرادها
في الملفات الأخرى. مسار البيانات يُقرأ من متغير البيئة DATA_PATH للسماح
بوضع قاعدة البيانات والملفات في موقع خارجي (مثل مجلد بيانات على القرص).
"""
import os
import platform
import secrets
from urllib.parse import unquote, urlparse
from pathlib import Path

from decouple import Config, RepositoryEnv
from decouple import config as env_config

# BASE_DIR = جذر المشروع (المجلد الذي يحوي manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# تحميل ملف .env إن وُجد (لا يُرفع على GitHub)
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    config = Config(RepositoryEnv(str(_env_file)))
else:
    config = env_config

# ---------------------------------------------------------------------------
# مسار البيانات: قاعدة البيانات + الملفات المرفوعة + الترخيص + السجلات
# يمكن تجاوزه عبر متغير البيئة DATA_PATH (مفيد للنسخة التشغيلية على Windows)
# ---------------------------------------------------------------------------
def _default_data_path():
    """اختيار مسار بيانات مستقل عن ملفات البرنامج."""
    if platform.system() == "Windows":
        root = os.environ.get("PROGRAMDATA") or os.environ.get("LOCALAPPDATA")
        if root:
            return str(Path(root) / "ClinicDataSystem")
    return str(Path.home() / ".clinic_data_system")


DATA_PATH = Path(
    config(
        "CLINIC_DATA_PATH",
        default=config("DATA_PATH", default=_default_data_path()),
    )
).expanduser().resolve()
DATABASE_DIR = DATA_PATH / "database"
UPLOADS_DIR = DATA_PATH / "uploads"
SECRETS_DIR = DATA_PATH / "secrets"
LOGS_DIR = DATA_PATH / "logs"
CACHE_DIR = DATA_PATH / "cache"
FILES_DIR = DATA_PATH / "Files"
IMPORTS_DIR = FILES_DIR / "Imported"
DOWNLOADS_DIR = FILES_DIR / "Downloads"
EXCEL_EXPORTS_DIR = FILES_DIR / "Excel"
ZIP_EXPORTS_DIR = FILES_DIR / "ZIP"
JSON_EXPORTS_DIR = FILES_DIR / "JSON"

# التأكد من وجود المجلدات
for _d in (DATABASE_DIR, UPLOADS_DIR, SECRETS_DIR, LOGS_DIR, CACHE_DIR, FILES_DIR, IMPORTS_DIR, DOWNLOADS_DIR, EXCEL_EXPORTS_DIR, ZIP_EXPORTS_DIR, JSON_EXPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# الأمان
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default=secrets.token_urlsafe(64))

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# ---------------------------------------------------------------------------
# التطبيقات
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.patients",
    "apps.visits",
    "apps.laboratory",
    "apps.referrals",
    "apps.ophthalmology",
    "apps.importer",
    "apps.backup",
    "apps.updater",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# الوسائط (Middleware)
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.core.middleware.PrivateNetworkHostMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # وسيط تسجيل العمليات المهمة (بدون بيانات حساسة)
    "apps.core.middleware.AuditLogMiddleware",
    # وسيط إجبار تغيير كلمة المرور المؤقتة
    "apps.accounts.middleware.ForcePasswordChangeMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.app_info",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# قاعدة البيانات: PostgreSQL للإنتاج، وSQLite فقط للتطوير/الاختبارات المحلية.
# ---------------------------------------------------------------------------
def _database_config():
    database_url = config("DATABASE_URL", default="").strip()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError("DATABASE_URL must use postgresql:// in production.")
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "localhost",
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {"sslmode": config("DB_SSLMODE", default="prefer")},
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DATABASE_DIR / "clinic.db"),
        "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
    }


DATABASES = {"default": _database_config()}

# ---------------------------------------------------------------------------
# نموذج المستخدم المخصص
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.LockoutModelBackend",
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# ---------------------------------------------------------------------------
# تشفير كلمات المرور (Argon2 أولاً — الأقوى)
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# إعدادات القفل بعد محاولات فاشلة
MAX_LOGIN_ATTEMPTS = config("MAX_LOGIN_ATTEMPTS", default=5, cast=int)
LOGIN_LOCKOUT_MINUTES = config("LOGIN_LOCKOUT_MINUTES", default=10, cast=int)

# ---------------------------------------------------------------------------
# اللغة والوقت
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ar"
TIME_ZONE = "Asia/Baghdad"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# الملفات الثابتة والوسائط
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = DATA_PATH / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = UPLOADS_DIR

# ---------------------------------------------------------------------------
# الجلسات (8 ساعات)
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = 28800  # 8 ساعات بالثواني
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(CACHE_DIR),
        "TIMEOUT": 300,
        "OPTIONS": {"MAX_ENTRIES": 2000},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# معلومات التطبيق
# ---------------------------------------------------------------------------
APP_NAME = "نظام إدارة بيانات ومرضى العيادة"
APP_VERSION = "1.5.5"
DB_SCHEMA_VERSION = "3"
FACILITY_NAME = config("FACILITY_NAME", default="عيادة الموصل الخيرية")
UPDATE_MANIFEST_URL = config("UPDATE_MANIFEST_URL", default="")
PUBLIC_BASE_URL = config("PUBLIC_BASE_URL", default="").strip().rstrip("/")

# ---------------------------------------------------------------------------
# السجلات (Logging) — لا تُسجَّل بيانات حساسة
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "clinic.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["file", "console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "clinic": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
