from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_department_department_type")]

    operations = [
        migrations.CreateModel(
            name="ReferenceValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف")),
                ("category", models.CharField(choices=[("department", "قسم"), ("doctor", "طبيب"), ("organizer", "منظّم"), ("lab_test", "فحص مختبري"), ("referral_destination", "جهة إحالة"), ("diagnosis", "تشخيص / حالة"), ("area", "منطقة سكن")], db_index=True, max_length=40, verbose_name="التصنيف")),
                ("canonical_name", models.CharField(max_length=255, verbose_name="الاسم الموحّد")),
                ("normalized_name", models.CharField(db_index=True, max_length=255, verbose_name="مفتاح المطابقة")),
                ("aliases", models.JSONField(blank=True, default=list, verbose_name="الصيغ الأصلية")),
                ("source_sheets", models.JSONField(blank=True, default=list, verbose_name="أوراق المصدر")),
                ("occurrence_count", models.PositiveIntegerField(default=0, verbose_name="عدد مرات الظهور")),
                ("needs_review", models.BooleanField(default=False, verbose_name="يحتاج مراجعة")),
                ("is_active", models.BooleanField(default=True, verbose_name="نشط")),
            ],
            options={"verbose_name": "قيمة مرجعية", "verbose_name_plural": "القيم المرجعية", "ordering": ["category", "canonical_name"]},
        ),
        migrations.AddConstraint(
            model_name="referencevalue",
            constraint=models.UniqueConstraint(fields=("category", "normalized_name"), name="uniq_reference_category_normalized"),
        ),
    ]
