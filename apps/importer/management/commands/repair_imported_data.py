from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from apps.importer.models import ImportBatch, SourceRow
from apps.importer.services import IMPORT_REPAIR_MARKER, import_batch_records, source_repeat_count
from apps.patients.models import Patient, PatientAddress, PatientContact, PatientName


def merge_duplicate_imported_patients():
    """Soft-merge duplicate Excel cards that share the workbook COUNTIF name."""
    from apps.importer.models import MergeDecision
    from apps.laboratory.models import LabOrder
    from apps.ophthalmology.models import EyeClinicVisit
    from apps.referrals.models import Referral
    from apps.visits.models import Visit

    duplicate_names = (
        PatientName.objects.filter(patient__source_type="excel", patient__deleted_at__isnull=True, is_primary=True)
        .values("normalized_name")
        .annotate(total=Count("patient_id", distinct=True))
        .filter(total__gt=1)
    )
    merged = 0
    for item in duplicate_names.iterator(chunk_size=200):
        patients = list(
            Patient.objects.filter(source_type="excel", names__normalized_name=item["normalized_name"])
            .distinct().order_by("created_at", "pk")
        )
        if len(patients) < 2:
            continue
        canonical = patients[0]
        for duplicate in patients[1:]:
            SourceRow.objects.filter(linked_patient=duplicate).update(linked_patient=canonical)
            Visit.objects.filter(patient=duplicate).update(patient=canonical)
            LabOrder.objects.filter(patient=duplicate).update(patient=canonical)
            Referral.objects.filter(patient=duplicate).update(patient=canonical)
            EyeClinicVisit.objects.filter(patient=duplicate).update(patient=canonical)
            MergeDecision.objects.filter(merged_patient=duplicate).update(merged_patient=canonical)

            for name in duplicate.names.all():
                if not canonical.names.filter(normalized_name=name.normalized_name).exists():
                    PatientName.objects.create(patient=canonical, full_name=name.full_name, is_primary=False, source=name.source)
            for contact in duplicate.contacts.all():
                if contact.value and not canonical.contacts.filter(value=contact.value).exists():
                    PatientContact.objects.create(patient=canonical, contact_type=contact.contact_type, value=contact.value, is_primary=False, notes=contact.notes)
            for address in duplicate.addresses.all():
                if address.text and not canonical.addresses.filter(text=address.text).exists():
                    PatientAddress.objects.create(patient=canonical, address_type=address.address_type, text=address.text, city=address.city, notes=address.notes)

            changed = []
            if canonical.gender == "unknown" and duplicate.gender != "unknown":
                canonical.gender = duplicate.gender
                changed.append("gender")
            if not canonical.date_of_birth and duplicate.date_of_birth:
                canonical.date_of_birth = duplicate.date_of_birth
                changed.append("date_of_birth")
            if canonical.approx_age_value is None and duplicate.approx_age_value is not None:
                canonical.approx_age_value = duplicate.approx_age_value
                canonical.approx_age_unit = duplicate.approx_age_unit
                changed.extend(["approx_age_value", "approx_age_unit"])
            if duplicate.imported_visit_count > canonical.imported_visit_count:
                canonical.imported_visit_count = duplicate.imported_visit_count
                changed.append("imported_visit_count")
            if changed:
                canonical.save(update_fields=list(dict.fromkeys(changed)) + ["updated_at"])
            duplicate.soft_delete()
            merged += 1
    return merged


class Command(BaseCommand):
    help = "ربط الصفوف التاريخية الناقصة وتصحيح عدد المراجعات المحسوب من Excel."

    def add_arguments(self, parser):
        parser.add_argument("--incomplete", action="store_true", help="إصلاح الدفعات غير المكتملة فقط.")

    @transaction.atomic
    def handle(self, *args, **options):
        batches = ImportBatch.objects.filter(import_type="patients")
        if options["incomplete"]:
            batches = batches.exclude(status="completed")
        duplicate_cards = (
            PatientName.objects.filter(patient__source_type="excel", patient__deleted_at__isnull=True, is_primary=True)
            .values("normalized_name").annotate(total=Count("patient_id", distinct=True)).filter(total__gt=1).exists()
        )
        if batches.exists() and not batches.exclude(notes__contains=IMPORT_REPAIR_MARKER).exists() and not SourceRow.objects.filter(batch__in=batches, linked_patient__isnull=True).exclude(status="rejected").exists() and not duplicate_cards:
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
        merged = merge_duplicate_imported_patients()
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
        self.stdout.write(self.style.SUCCESS(f"Repaired {repaired} counters, linked {imported} imported rows, and merged {merged} duplicate cards."))
