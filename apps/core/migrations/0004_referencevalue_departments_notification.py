from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_referencevalue"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="referencevalue",
            name="departments",
            field=models.ManyToManyField(blank=True, help_text="تُستخدم خصوصاً لربط الطبيب بقسم أو أكثر كما ورد في ملفات المصدر.", related_name="reference_values", to="core.department", verbose_name="الأقسام المرتبطة"),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")),
                ("event_type", models.CharField(choices=[("patient_created", "تسجيل مريض"), ("patient_updated", "تعديل مريض"), ("import_completed", "اكتمال استيراد"), ("import_failed", "خطأ استيراد"), ("system", "حدث نظام")], default="system", max_length=40, verbose_name="نوع الحدث")),
                ("title", models.CharField(max_length=160, verbose_name="العنوان")),
                ("message", models.CharField(blank=True, default="", max_length=300, verbose_name="الرسالة")),
                ("object_type", models.CharField(blank=True, default="", max_length=80, verbose_name="نوع السجل المرتبط")),
                ("object_id", models.CharField(blank=True, default="", max_length=100, verbose_name="معرّف السجل المرتبط")),
                ("target_url", models.CharField(blank=True, default="", max_length=300, verbose_name="الرابط")),
                ("read_at", models.DateTimeField(blank=True, null=True, verbose_name="قُرئ في")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL, verbose_name="المستخدم")),
            ],
            options={"verbose_name": "إشعار", "verbose_name_plural": "الإشعارات", "ordering": ["-created_at"]},
        ),
    ]
