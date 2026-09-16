import re

from django.db import migrations, models


def normalize(value):
    value = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", (value or "").lower())
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}))
    return re.sub(r"\s+", " ", value).strip()


def populate_normalized_names(apps, schema_editor):
    PatientName = apps.get_model("patients", "PatientName")
    for item in PatientName.objects.all().only("pk", "full_name").iterator(chunk_size=1000):
        item.normalized_name = normalize(item.full_name)
        item.save(update_fields=["normalized_name"])


class Migration(migrations.Migration):
    dependencies = [("patients", "0004_patient_source_metadata")]
    operations = [
        migrations.AddField(
            model_name="patientname",
            name="normalized_name",
            field=models.CharField(blank=True, db_index=True, default="", max_length=255, verbose_name="الاسم المطبّع للبحث"),
        ),
        migrations.RunPython(populate_normalized_names, migrations.RunPython.noop),
    ]
