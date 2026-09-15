"""
إعدادات المشغّل (Launcher).

ملف مستقل عن إعدادات Django يحدد مسار البيانات والمنفذ. يمكن للمستخدم
تعديله لتغيير موقع تخزين البيانات دون لمس شيفرة المشروع.
"""
import os
from pathlib import Path

# جذر المشروع
BASE_DIR = Path(__file__).resolve().parent

# مسار البيانات (قاعدة البيانات + المرفوعات + السجلات + الترخيص)
# يمكن تجاوزه عبر متغير البيئة DATA_PATH.
DATA_PATH = os.environ.get("DATA_PATH", str(BASE_DIR / "data"))

# إعدادات الخادم المحلي
HOST = "127.0.0.1"
PORT = 8765
THREADS = 4  # خفيف على ذاكرة 8GB

# عنوان الواجهة
APP_URL = f"http://{HOST}:{PORT}"

# عنوان نافذة سطح المكتب
WINDOW_TITLE = "نظام إدارة بيانات ومرضى العيادة"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
