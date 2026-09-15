import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.backup.services import sha256_file


class Command(BaseCommand):
    help = "استعادة نسخة clinicbackup بعد إيقاف التطبيق"

    def add_arguments(self, parser):
        parser.add_argument("backup_file")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("أوقف التطبيق ثم أعد الأمر مع --confirm")
        source = Path(options["backup_file"]).resolve()
        if not source.is_file():
            raise CommandError("ملف النسخة غير موجود")
        db_path = Path(settings.DATABASES["default"]["NAME"])
        with tempfile.TemporaryDirectory() as temporary, zipfile.ZipFile(source) as archive:
            if not {"clinic.db", "manifest.json"}.issubset(archive.namelist()):
                raise CommandError("تنسيق النسخة غير صالح")
            archive.extract("clinic.db", temporary); archive.extract("manifest.json", temporary)
            restored = Path(temporary) / "clinic.db"
            manifest = json.loads((Path(temporary) / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("format") != "ClinicDataBackup/1" or sha256_file(restored) != manifest.get("database_sha256"):
                raise CommandError("فشل التحقق من بصمة قاعدة البيانات")
            connection.close()
            safety = Path(settings.DATA_PATH) / "backups" / "pre_restore"
            safety.mkdir(parents=True, exist_ok=True)
            if db_path.exists():
                shutil.copy2(db_path, safety / f"clinic-before-restore-{timezone.localtime().strftime('%Y%m%d-%H%M%S')}.db")
            shutil.copy2(restored, db_path)
        self.stdout.write(self.style.SUCCESS("تمت الاستعادة بنجاح. شغّل التطبيق وطبّق الترحيلات."))
