"""لوحة إدارة الاستيراد."""
from django.contrib import admin

from .models import (
    DataIssue,
    ImportBatch,
    ImportFile,
    ImportSheet,
    MatchCandidate,
    MergeDecision,
    ReviewDecision,
    SourceRow,
)


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "status", "total_rows", "created_at")
    list_filter = ("status",)


admin.site.register(ImportFile)
admin.site.register(ImportSheet)
admin.site.register(SourceRow)
admin.site.register(DataIssue)
admin.site.register(ReviewDecision)
admin.site.register(MatchCandidate)
admin.site.register(MergeDecision)
