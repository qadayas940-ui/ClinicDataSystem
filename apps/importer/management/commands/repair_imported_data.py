from django.core.management.base import BaseCommand
from django.db import transaction

from apps.importer.models import ImportBatch, SourceRow
from apps.importer.services import IMPORT_REPAIR_MARKER, import_batch_records, source_repeat_count
from apps.patients.models import Patient


class Command(BaseCommand):
    help = "ربط الصفوف التاريخية الناقصة وتصحيح عدد المراجعات المحسوب من Excel."

    @transaction.atomic
    def handle(self, *args, **options):
        batches = ImportBatch.objects.filter(import_type="patients")
        if batches.exists() and not batches.exclude(notes__contains=IMPORT_REPAIR_MARKER).exists() and not SourceRow.objects.filter(batch__in=batches, linked_patient__isnull=True).exclude(status="rejected").exists():
            self.stdout.write("Imported data was already repaired.")
            return
        repaired = 0
        for patient in Patient.objects.filter(source_type="excel").iterator(chunk_size=500):
            counts = []
            for raw_data in patient.source_rows.values_list("raw_data", flat=True).iterator(chunk_size=100):
                count = source_repeat_count(raw_data)
                if count:
                    counts.append(count)
            correct = max(counts, default=0)
            if patient.imported_visit_count != correct:
                patient.imported_visit_count = correct
                patient.save(update_fields=["imported_visit_count", "updated_at"])
                repaired += 1

        imported = 0
        for batch in batches:
            if SourceRow.objects.filter(batch=batch, linked_patient__isnull=True).exclude(status="rejected").exists():
                imported += import_batch_records(batch, batch.imported_by)
        # A second pass is required because the repair above may have linked
        # previously pending rows to an existing patient.
        for patient in Patient.objects.filter(source_type="excel").iterator(chunk_size=500):
            correct = max(
                (source_repeat_count(raw) for raw in patient.source_rows.values_list("raw_data", flat=True).iterator(chunk_size=100)),
                default=0,
            )
            if patient.imported_visit_count != correct:
                patient.imported_visit_count = correct
                patient.save(update_fields=["imported_visit_count", "updated_at"])
                repaired += 1

        from django.db.models import Count
        from django.utils import timezone
        from apps.ophthalmology.models import EyeClinicVisit

        eye_rows = SourceRow.objects.filter(sheet__sheet_name__in=["عيادة العيون", "عياده العيون"], linked_patient__isnull=False).values("linked_patient_id").annotate(total=Count("id"))
        for item in eye_rows.iterator(chunk_size=500):
            existing = EyeClinicVisit.objects.filter(patient_id=item["linked_patient_id"]).count()
            EyeClinicVisit.objects.bulk_create([
                EyeClinicVisit(patient_id=item["linked_patient_id"], visit_date=timezone.now(), status="open")
                for _ in range(max(0, item["total"] - existing))
            ])
        for batch in batches:
            if IMPORT_REPAIR_MARKER not in batch.notes:
                batch.notes = f"{batch.notes}\n{IMPORT_REPAIR_MARKER}".strip()
                batch.save(update_fields=["notes", "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"Repaired {repaired} counters and linked {imported} imported rows."))
