from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("importer", "0002_importbatch_previous_batch_sourcerow_classification_and_more")]
    operations = [migrations.AddField(model_name="sourcerow", name="imported_at", field=models.DateTimeField(blank=True, null=True, verbose_name="تم إدراجه في"))]
