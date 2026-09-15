"""
إعدادات المشغّل (Launcher).

ملف مستقل عن إعدادات Django يحدد مسار البيانات والمنفذ. يمكن للمستخدم
تعديله لتغيير موقع تخزين البيانات دون لمس شيفرة المشروع.
"""
import json
import os
import platform
import sys
from pathlib import Path

# جذر المشروع
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

def _config_home():
    if platform.system() == "Windows":
        root = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(root) / "ClinicDataSystem"
    return Path.home() / ".clinic_data_system"


CONFIG_HOME = _config_home()
CONFIG_FILE = CONFIG_HOME / "desktop.json"


def _load_desktop_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


DESKTOP_CONFIG = _load_desktop_config()


def _default_data_path():
    if platform.system() == "Windows":
        d_drive_path = Path("D:/GOODJobe/mmmmm/Data")
        if d_drive_path.parent.exists():
            return str(d_drive_path)
    return str(CONFIG_HOME / "data")


DATA_PATH = os.environ.get("CLINIC_DATA_PATH") or DESKTOP_CONFIG.get("data_path") or _default_data_path()

# إعدادات الخادم المحلي
ALLOW_LAN = os.environ.get("CLINIC_ALLOW_LAN", str(DESKTOP_CONFIG.get("allow_lan", False))).lower() in {"1", "true", "yes"}
HOST = "0.0.0.0" if ALLOW_LAN else "127.0.0.1"
PORT = int(os.environ.get("CLINIC_PORT", DESKTOP_CONFIG.get("port", 8765)))
THREADS = 4  # خفيف على ذاكرة 8GB

# عنوان الواجهة
APP_URL = f"http://127.0.0.1:{PORT}"

# عنوان نافذة سطح المكتب
WINDOW_TITLE = "نظام إدارة بيانات ومرضى العيادة"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
