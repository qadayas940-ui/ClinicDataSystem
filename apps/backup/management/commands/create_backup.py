from django.core.management.base import BaseCommand

from apps.backup.services import create_database_backup


class Command(BaseCommand):
    help = "إنشاء نسخة احتياطية كاملة بصيغة clinicbackup"

    def add_arguments(self, parser):
        parser.add_argument("--automatic", action="store_true")

    def handle(self, *args, **options):
        item = create_database_backup(backup_type="automatic" if options["automatic"] else "manual")
        self.stdout.write(self.style.SUCCESS(item.file_path))
