from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("core", "0004_referencevalue_departments_notification")]
    operations = [migrations.DeleteModel(name="LicenseState")]
