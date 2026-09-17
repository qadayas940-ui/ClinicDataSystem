from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alter_notification_event_type"),
        ("referrals", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="referral",
            name="referring_doctor_reference",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"category": "doctor"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="referred_cases",
                to="core.referencevalue",
                verbose_name="الطبيب المُحيل من السجل المرجعي",
            ),
        ),
    ]
