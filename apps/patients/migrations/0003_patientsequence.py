from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("patients", "0002_alter_patientcontact_value_and_more")]

    operations = [
        migrations.CreateModel(
            name="PatientSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField(unique=True, verbose_name="السنة")),
                ("last_value", models.PositiveBigIntegerField(default=0, verbose_name="آخر تسلسل")),
            ],
            options={"verbose_name": "تسلسل أرقام المرضى", "verbose_name_plural": "تسلسلات أرقام المرضى"},
        ),
    ]
