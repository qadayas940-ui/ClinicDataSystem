from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("importer", "0003_sourcerow_imported_at")]
    operations = [
        migrations.AlterField(
            model_name="importbatch",
            name="import_type",
            field=models.CharField(blank=True, choices=[("patients", "بيانات المرضى والزيارات"), ("doctors", "الأطباء"), ("departments", "الأقسام"), ("organizers", "المنظمون"), ("other", "بيانات أخرى")], default="patients", max_length=80, verbose_name="نوع الاستيراد"),
        )
    ]
