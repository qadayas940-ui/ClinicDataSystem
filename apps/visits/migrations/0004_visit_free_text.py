from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("visits", "0003_visit_type_source")]
    operations = [
        migrations.AddField(
            model_name="visit", name="department_text",
            field=models.CharField("القسم المكتوب", max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="visit", name="doctor_text",
            field=models.CharField("اسم الطبيب المكتوب", max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="visit", name="organizer_text",
            field=models.CharField("اسم المنظّم المكتوب", max_length=255, blank=True, default=""),
        ),
    ]
