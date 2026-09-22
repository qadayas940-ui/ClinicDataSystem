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
import hashlib
import secrets
import shutil
import sys
import threading
import time
import traceback
import webbrowser
from io import StringIO
from datetime import datetime
from datetime import timezone as datetime_timezone
from pathlib import Path
from urllib.request import urlopen

import launcher_config as cfg


_INSTANCE_MUTEX_HANDLE = None


def _startup_log_path():
    try:
        log_dir = Path(cfg.DATA_PATH).expanduser().resolve() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "startup.log"
    except OSError:
        fallback = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ClinicDataSystem"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback / "startup.log"


def _write_startup_log(message):
    path = _startup_log_path()
    stamp = datetime.now(datetime_timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{stamp}] {message}\n")
    return path


def _show_error_dialog(message, log_path):
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0,
            f"{message}\n\nتم حفظ التفاصيل في:\n{log_path}",
            "ClinicDataSystem - خطأ في التشغيل",
            0x10,
        )
    except Exception:
        return


def _acquire_server_instance():
    """Ensure only one local process can prepare SQLite and host the server."""
    global _INSTANCE_MUTEX_HANDLE
    if os.name != "nt":
        return True
    import ctypes

    identity = f"{Path(cfg.DATA_PATH).expanduser().resolve()}|{cfg.PORT}".lower()
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, f"Local\\ClinicDataSystem-{suffix}")
    if not handle:
        return True
    _INSTANCE_MUTEX_HANDLE = handle
    return ctypes.windll.kernel32.GetLastError() != 183


def _setup_environment():
    """ضبط متغيرات البيئة قبل تحميل Django."""
    _write_startup_log(f"Starting ClinicDataSystem. base={cfg.BASE_DIR}, data={cfg.DATA_PATH}, url={cfg.APP_URL}")
    if sys.stdout is None:
        sys.stdout = StringIO()
    if sys.stderr is None:
        sys.stderr = StringIO()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    data_path = Path(cfg.DATA_PATH).expanduser().resolve()
    for child in ("database", "uploads", "secrets", "logs", "backups", "cache", "Files", "Files/Imported", "Files/Downloads", "Files/Excel", "Files/ZIP", "Files/JSON"):
        (data_path / child).mkdir(parents=True, exist_ok=True)
    secret_file = data_path / "secrets" / "secret.key"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(64), encoding="utf-8")
    os.environ.setdefault("CLINIC_DATA_PATH", str(data_path))
    os.environ.setdefault("SECRET_KEY", secret_file.read_text(encoding="utf-8").strip())
    if cfg.DATABASE_URL:
        os.environ.setdefault("DATABASE_URL", cfg.DATABASE_URL)
    if cfg.ALLOW_SQLITE_PRODUCTION:
        os.environ.setdefault("ALLOW_SQLITE_PRODUCTION", "true")
    os.environ.setdefault("CLINIC_ALLOW_LAN", "true" if cfg.ALLOW_LAN else "false")
    os.environ.setdefault("CLINIC_PORT", str(cfg.PORT))
    # افرض القيمة الصحيحة على نسخة سطح المكتب؛ قد تبقى قيمة قديمة في بيئة
    # Windows، وsetdefault كان يتركها فيسبب 400 للأجهزة الأخرى.
    os.environ["ALLOWED_HOSTS"] = "*" if cfg.ALLOW_LAN else "127.0.0.1,localhost"
    sys.path.insert(0, str(cfg.BASE_DIR))


def _run_migrations():
    """Run only blocking first-run/update work before opening the server."""
    import django
    from django.core.management import call_command

    django.setup()
    from django.conf import settings
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    command_output = StringIO()
    executor = MigrationExecutor(connection)
    pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    is_sqlite = settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    db_path = Path(settings.DATABASES["default"]["NAME"]) if is_sqlite else None
    if pending and db_path and db_path.exists() and db_path.stat().st_size:
        destination = Path(settings.DATA_PATH) / "backups" / "pre_update"
        destination.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(datetime_timezone.utc).strftime("%Y%m%d-%H%M%S")
        shutil.copy2(db_path, destination / f"clinic-before-update-{stamp}.db")
    if pending:
        call_command("migrate", interactive=False, verbosity=1, stdout=command_output, stderr=command_output)

    marker = Path(settings.DATA_PATH) / "secrets" / f"prepared-{settings.APP_VERSION}.ok"
    if not marker.exists():
        call_command("init_data", verbosity=0, stdout=command_output, stderr=command_output)
        call_command("collectstatic", interactive=False, verbosity=0, stdout=command_output, stderr=command_output)
        marker.write_text(datetime.now(datetime_timezone.utc).isoformat(), encoding="utf-8")
    output = command_output.getvalue().strip()
    if output:
        _write_startup_log(output)


def _run_background_maintenance():
    """Repair unfinished imports and create the daily backup without blocking the UI."""
    from datetime import timedelta
    from django.core.management import call_command
    from django.db import close_old_connections
    from django.utils import timezone
    from apps.core.models import BackupHistory

    close_old_connections()
    output = StringIO()
    try:
        call_command("repair_imported_data", "--incomplete", verbosity=0, stdout=output, stderr=output)
        if not BackupHistory.objects.filter(status="success", created_at__gte=timezone.now() - timedelta(days=1)).exists():
            call_command("create_backup", automatic=True, verbosity=0, stdout=output, stderr=output)
    except Exception as exc:
        _write_startup_log(f"Background maintenance warning: {exc}\n{traceback.format_exc()}")
    finally:
        close_old_connections()
    if output.getvalue().strip():
        _write_startup_log(output.getvalue().strip())


def _start_server(holder):
    """تشغيل خادم Waitress."""
    try:
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
    except Exception as exc:  # noqa: BLE001
        holder["error"] = exc
        holder["traceback"] = traceback.format_exc()


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


def _open_client(url):
    """يفتح واجهة الخادم المركزي دون تشغيل قاعدة أو خادم محلي على جهاز الموظف."""
    try:
        import webview

        webview.create_window(cfg.WINDOW_TITLE, url, width=cfg.WINDOW_WIDTH, height=cfg.WINDOW_HEIGHT)
        webview.start()
    except Exception as exc:  # noqa: BLE001
        log_path = _write_startup_log(f"تعذر فتح نافذة العميل للخادم {url}: {exc}\n{traceback.format_exc()}")
        _show_error_dialog(f"تعذر فتح نافذة البرنامج. سيتم فتح الرابط في المتصفح:\n{url}", log_path)
        webbrowser.open(url)


def main():
    """نقطة الدخول الرئيسية للمشغّل."""
    try:
        if cfg.REMOTE_SERVER_URL:
            _write_startup_log(f"Starting central-server client. url={cfg.REMOTE_SERVER_URL}")
            _open_client(cfg.REMOTE_SERVER_URL)
            return
        _setup_environment()

        # The installer starts the persistent scheduled server first, then opens
        # this lightweight client.  It must never touch SQLite while the server
        # is applying migrations or repairing imported data.
        if "--client" in sys.argv:
            _write_startup_log("Waiting for the local clinic server client connection.")
            if not _wait_for_server(timeout=600):
                raise RuntimeError("انتهت مهلة انتظار خادم العيادة المحلي.")
            _open_client(cfg.APP_URL)
            return

        if not _acquire_server_instance():
            _write_startup_log("A local server instance already owns the database; opening its client.")
            if not _wait_for_server(timeout=600):
                raise RuntimeError("قاعدة البيانات قيد التجهيز، وتعذر الاتصال بالخادم خلال المهلة المحددة.")
            if "--server" not in sys.argv:
                _open_client(cfg.APP_URL)
            return

        print("جارٍ تجهيز قاعدة البيانات…")
        _run_migrations()

        print("جارٍ تشغيل الخادم…")
        server_holder = {}
        server_thread = threading.Thread(target=_start_server, args=(server_holder,), daemon=True)
        server_thread.start()

        if not _wait_for_server():
            if server_holder.get("error"):
                raise RuntimeError(f"تعذّر تشغيل الخادم: {server_holder['error']}\n{server_holder.get('traceback', '')}")
            print("خطأ: تعذّر تشغيل الخادم في الوقت المحدد.")
            sys.exit(1)

        print(f"الخادم يعمل على {cfg.APP_URL}")
        threading.Thread(target=_run_background_maintenance, name="clinic-maintenance", daemon=True).start()
        if cfg.ALLOW_LAN:
            from apps.core.network import discover_lan_addresses, preferred_lan_url
            lan_url = preferred_lan_url(cfg.PORT)
            lan_urls = [f"http://{address}:{cfg.PORT}" for address in discover_lan_addresses()]
            _write_startup_log(f"LAN access enabled. preferred={lan_url}, candidates={lan_urls}")
            share_file = Path(cfg.DATA_PATH).expanduser().resolve() / "Clinic-Network-Link.txt"
            share_file.write_text(
                "ClinicDataSystem LAN URL\n" + lan_url + "\n\n"
                "Keep the server PC running and allow ClinicDataSystem through Windows Firewall.\n",
                encoding="utf-8",
            )
            print(f"رابط أجهزة العيادة: {lan_url}")

        if "--server" in sys.argv or os.environ.get("CLINIC_HEADLESS", "").lower() in {"1", "true", "yes"}:
            _write_startup_log("ClinicDataSystem is running in headless LAN/server mode.")
            server_thread.join()
            return

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
        except Exception as exc:  # noqa: BLE001
            message = (
                "تعذّر فتح نافذة سطح المكتب. "
                f"سيتم فتح النظام في المتصفح على العنوان: {cfg.APP_URL}. "
                f"تفاصيل الخطأ: {exc}"
            )
            log_path = _write_startup_log(message + "\n" + traceback.format_exc())
            print(message)
            _show_error_dialog(message, log_path)
            webbrowser.open(cfg.APP_URL)
            server_thread.join()

    except Exception as exc:  # noqa: BLE001
        details = traceback.format_exc()
        log_path = _write_startup_log(f"حدث خطأ أثناء تشغيل التطبيق: {exc}\n{details}")
        print("حدث خطأ أثناء تشغيل التطبيق:")
        print(str(exc))
        _show_error_dialog(f"تعذر تشغيل ClinicDataSystem.\n\nالخطأ: {exc}", log_path)
        sys.exit(1)


if __name__ == "__main__":
    main()
