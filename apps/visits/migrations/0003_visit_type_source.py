from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("visits", "0002_visit_reference_people")]
    operations = [
        migrations.AddField(
            model_name="visit", name="visit_type",
            field=models.CharField(choices=[("clinic", "زيارة عيادة"), ("follow_up", "مراجعة / متابعة"), ("laboratory", "مختبر"), ("referral", "إحالة"), ("imported_historical", "زيارة تاريخية مستوردة"), ("other", "أخرى")], db_index=True, default="clinic", max_length=30, verbose_name="نوع الزيارة"),
        ),
        migrations.AddField(
            model_name="visit", name="source",
            field=models.CharField(db_index=True, default="manual", max_length=30, verbose_name="المصدر"),
        ),
    ]
