from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0005_remove_license_state")]
    operations = [
        migrations.AlterField(
            model_name="notification",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("patient_created", "تسجيل مريض"),
                    ("patient_updated", "تعديل مريض"),
                    ("visit_created", "تسجيل زيارة"),
                    ("import_completed", "اكتمال استيراد"),
                    ("import_failed", "خطأ استيراد"),
                    ("system", "حدث نظام"),
                ],
                default="system", max_length=40, verbose_name="نوع الحدث",
            ),
        ),
    ]
