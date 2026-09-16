from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("core", "0004_referencevalue_departments_notification"), ("visits", "0001_initial")]
    operations = [
        migrations.AddField(model_name="visit", name="doctor_reference", field=models.ForeignKey(blank=True, limit_choices_to={"category": "doctor"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="doctor_visits", to="core.referencevalue", verbose_name="اسم الطبيب من السجل المرجعي")),
        migrations.AddField(model_name="visit", name="organizer_reference", field=models.ForeignKey(blank=True, limit_choices_to={"category": "organizer"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="organized_reference_visits", to="core.referencevalue", verbose_name="اسم المنظّم من السجل المرجعي")),
    ]
