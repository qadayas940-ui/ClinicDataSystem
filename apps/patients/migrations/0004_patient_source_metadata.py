from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("patients", "0003_patientsequence")]
    operations = [
        migrations.AddField(model_name="patient", name="additional_data", field=models.JSONField(blank=True, default=dict, verbose_name="البيانات الإضافية")),
        migrations.AddField(model_name="patient", name="external_id", field=models.CharField(blank=True, db_index=True, default="", max_length=120, verbose_name="المعرّف الخارجي")),
        migrations.AddField(model_name="patient", name="imported_at", field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الاستيراد")),
        migrations.AddField(model_name="patient", name="source_file", field=models.CharField(blank=True, default="", max_length=255, verbose_name="ملف المصدر")),
        migrations.AddField(model_name="patient", name="source_row", field=models.PositiveIntegerField(blank=True, null=True, verbose_name="صف المصدر")),
        migrations.AddField(model_name="patient", name="source_sheet", field=models.CharField(blank=True, default="", max_length=200, verbose_name="ورقة المصدر")),
        migrations.AddField(model_name="patient", name="source_type", field=models.CharField(blank=True, default="manual", max_length=40, verbose_name="نوع المصدر")),
    ]
