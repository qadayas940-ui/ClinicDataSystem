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
import sys
import threading
import time
from urllib.request import urlopen

import launcher_config as cfg


def _setup_environment():
    """ضبط متغيرات البيئة قبل تحميل Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    os.environ.setdefault("DATA_PATH", cfg.DATA_PATH)
    sys.path.insert(0, str(cfg.BASE_DIR))


def _run_migrations():
    """تطبيق ترحيلات قاعدة البيانات (إنشاؤها عند أول تشغيل)."""
    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate", interactive=False, verbosity=1)
    # تجميع الملفات الثابتة إن لزم
    try:
        call_command("collectstatic", interactive=False, verbosity=0)
    except Exception:
        pass


def _start_server():
    """تشغيل خادم Waitress."""
    from waitress import serve

    from config.wsgi import application

    serve(
        application,
        host=cfg.HOST,
        port=cfg.PORT,
        threads=cfg.THREADS,
        _quiet=True,
    )


def _wait_for_server(timeout=30):
    """انتظار جاهزية الخادم قبل فتح النافذة."""
    deadline = time.time() + timeout
    health_url = f"{cfg.APP_URL}/api/health/"
    while time.time() < deadline:
        try:
            with urlopen(health_url, timeout=2) as resp:
                if resp.status in (200, 503):
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    """نقطة الدخول الرئيسية للمشغّل."""
    try:
        _setup_environment()
        print("جارٍ تجهيز قاعدة البيانات…")
        _run_migrations()

        print("جارٍ تشغيل الخادم…")
        server_thread = threading.Thread(target=_start_server, daemon=True)
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
