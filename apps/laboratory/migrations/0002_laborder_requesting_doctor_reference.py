from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alter_notification_event_type"),
        ("laboratory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="laborder",
            name="requesting_doctor_reference",
            field=models.ForeignKey(
                blank=True,
                help_text="يُستخدم دليل الأطباء المشترك، مع إبقاء حساب الطبيب القديم للتوافق مع السجلات السابقة.",
                limit_choices_to={"category": "doctor", "is_active": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="requested_lab_orders",
                to="core.referencevalue",
                verbose_name="الطبيب الطالب من دليل الأطباء",
            ),
        ),
    ]
