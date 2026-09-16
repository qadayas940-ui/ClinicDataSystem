from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render

from apps.core.models import BackupHistory
from apps.core.utils import log_audit, owner_required

from .services import create_csv_export, create_database_backup, create_excel_export, create_json_export


@owner_required
def backup_list(request):
    return render(request, "backup/list.html", {"backups": BackupHistory.objects.all()[:50]})


@owner_required
def backup_create(request):
    if request.method == "POST":
        try:
            item = create_database_backup(request.user)
            log_audit(request, "export", "BackupHistory", item.pk, item.checksum)
            messages.success(request, "تم إنشاء نسخة احتياطية كاملة والتحقق من بصمتها.")
        except Exception:
            messages.error(request, "تعذر إنشاء النسخة الاحتياطية. راجع سجل النظام أو إعداد اتصال قاعدة البيانات.")
    return redirect("backup:list")


@owner_required
def backup_download(request, pk):
    item = BackupHistory.objects.get(pk=pk, status="success")
    path = Path(item.file_path).resolve()
    backup_root = (Path(settings.DATA_PATH) / "backups").resolve()
    if not path.is_file() or backup_root not in path.parents: raise Http404
    log_audit(request, "export", "BackupHistory", item.pk, "download")
    return FileResponse(path.open("rb"), as_attachment=True, filename=path.name)


@owner_required
def excel_export(request):
    return _export_response(request, create_excel_export, "Workbook")


@owner_required
def csv_export(request):
    return _export_response(request, create_csv_export, "CSV archive")


@owner_required
def json_export(request):
    return _export_response(request, create_json_export, "JSON export")


def _export_response(request, creator, object_type):
    try:
        path = creator()
    except Exception:
        messages.error(request, "تعذر تصدير البيانات. لم تُحذف أو تتغير أي بيانات.")
        return redirect("backup:list")
    log_audit(request, "export", object_type, object_repr=path.name)
    return FileResponse(path.open("rb"), as_attachment=True, filename=path.name)
