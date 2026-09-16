import re

from django.db import migrations, models


def backfill_visit_counts(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    for patient in Patient.objects.filter(source_type="excel").iterator(chunk_size=1000):
        extra = patient.additional_data or {}
        sources = extra.get("source_columns") or {}
        raw = extra.get("imported_visit_count")
        if raw in (None, ""):
            for key, value in sources.items():
                if "تكرار" in str(key) or "مراجعات" in str(key):
                    raw = value
                    break
        match = re.search(r"\d+", str(raw or ""))
        if match:
            patient.imported_visit_count = min(int(match.group()), 100000)
            patient.save(update_fields=["imported_visit_count"])


class Migration(migrations.Migration):
    dependencies = [("patients", "0005_patientname_normalized_name")]
    operations = [
        migrations.AddField(
            model_name="patient",
            name="imported_visit_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="يحفظ العدد التاريخي الوارد في Excel عندما لا تتوفر تفاصيل كل زيارة.",
                verbose_name="عدد المراجعات حسب الملف المستورد",
            ),
        ),
        migrations.RunPython(backfill_visit_counts, migrations.RunPython.noop),
    ]
