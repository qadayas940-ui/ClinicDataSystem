"""
مشغّل تطبيق سطح المكتب لنظام إدارة بيانات ومرضى العيادة.

يقوم بـ:
1. ضبط مسار البيانات ومتغيرات البيئة.
2. تطبيق ترحيلات قاعدة البيانات تلقائياً عند أول تشغيل.
3. تشغيل خادم Waitress في خيط منفصل.
4. فتح نافذة pywebview تعرض الواجهة كتطبيق سطح مكتب.

يعالج الأخطاء ويعرضها للمستخدم برسائل عربية مفهومة.
"""
import os
import secrets
import shutil
import sys
import threading
import time
from datetime import datetime
from datetime import timezone as datetime_timezone
from pathlib import Path
from urllib.request import urlopen

import launcher_config as cfg


def _setup_environment():
    """ضبط متغيرات البيئة قبل تحميل Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    data_path = Path(cfg.DATA_PATH).expanduser().resolve()
    for child in ("database", "uploads", "license", "logs", "backups"):
        (data_path / child).mkdir(parents=True, exist_ok=True)
    secret_file = data_path / "license" / "secret.key"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(64), encoding="utf-8")
    os.environ.setdefault("CLINIC_DATA_PATH", str(data_path))
    os.environ.setdefault("SECRET_KEY", secret_file.read_text(encoding="utf-8").strip())
    os.environ.setdefault("ALLOWED_HOSTS", "127.0.0.1,localhost,*" if cfg.ALLOW_LAN else "127.0.0.1,localhost")
    sys.path.insert(0, str(cfg.BASE_DIR))


def _run_migrations():
    """تطبيق ترحيلات قاعدة البيانات (إنشاؤها عند أول تشغيل)."""
    import django
    from django.core.management import call_command

    django.setup()
    from django.conf import settings

    db_path = Path(settings.DATABASES["default"]["NAME"])
    if db_path.exists() and db_path.stat().st_size:
        destination = Path(settings.DATA_PATH) / "backups" / "pre_update"
        destination.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(datetime_timezone.utc).strftime("%Y%m%d-%H%M%S")
        shutil.copy2(db_path, destination / f"clinic-before-update-{stamp}.db")
    call_command("migrate", interactive=False, verbosity=1)
    call_command("init_data", verbosity=0)
    call_command("collectstatic", interactive=False, verbosity=0)
    from datetime import timedelta

    from django.utils import timezone

    from apps.core.models import BackupHistory

    if not BackupHistory.objects.filter(status="success", created_at__gte=timezone.now() - timedelta(days=1)).exists():
        call_command("create_backup", automatic=True, verbosity=0)


def _start_server(holder):
    """تشغيل خادم Waitress."""
    from waitress.server import create_server

    from config.wsgi import application

    server = create_server(
        application,
        host=cfg.HOST,
        port=cfg.PORT,
        threads=cfg.THREADS,
    )
    holder["server"] = server
    server.run()


def _wait_for_server(timeout=30):
    """انتظار جاهزية الخادم قبل فتح النافذة."""
    deadline = time.time() + timeout
    health_url = f"{cfg.APP_URL}/api/health/"
    while time.time() < deadline:
        try:
            with urlopen(health_url, timeout=2) as resp:
                if resp.status in (200, 503):
                    return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    """نقطة الدخول الرئيسية للمشغّل."""
    try:
        _setup_environment()
        print("جارٍ تجهيز قاعدة البيانات…")
        _run_migrations()

        print("جارٍ تشغيل الخادم…")
        server_holder = {}
        server_thread = threading.Thread(target=_start_server, args=(server_holder,), daemon=True)
        server_thread.start()

        if not _wait_for_server():
            print("خطأ: تعذّر تشغيل الخادم في الوقت المحدد.")
            sys.exit(1)

        print(f"الخادم يعمل على {cfg.APP_URL}")

        # فتح نافذة سطح المكتب
        try:
            import webview

            webview.create_window(
                cfg.WINDOW_TITLE,
                cfg.APP_URL,
                width=cfg.WINDOW_WIDTH,
                height=cfg.WINDOW_HEIGHT,
            )
            webview.start()
            server = server_holder.get("server")
            if server:
                server.close()
        except ImportError:
            # في حال عدم توفّر pywebview، أبقِ الخادم يعمل وأخبر المستخدم
            print(
                "تعذّر تحميل واجهة سطح المكتب (pywebview غير مثبّت). "
                f"افتح المتصفح على العنوان: {cfg.APP_URL}"
            )
            server_thread.join()

    except Exception as exc:  # noqa: BLE001
        print("حدث خطأ أثناء تشغيل التطبيق:")
        print(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
