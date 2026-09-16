# ClinicDataSystem

نظام سطح مكتب عربي لإدارة ملفات المرضى والزيارات والمختبر والإحالات وعيادة العيون، مع استيراد Excel آمن ونسخ احتياطي مستقل عن ملفات البرنامج.

## الحالة الحالية

هذه نسخة تشغيلية مستمرة بلا انتهاء زمني. واجهات التشغيل الأساسية، حسابات الموظفين، الأقسام، الاستيراد المرحلي، سجل التدقيق، النسخ الكامل، وتصدير Excel موجودة على الفرع `codex/v1-complete`. يستخدم النشر متعدد المستخدمين PostgreSQL مركزياً، بينما يظل SQLite خياراً محلياً صريحاً للاختبار فقط.

> لا تضع ملفات المرضى أو قاعدة البيانات أو مفاتيح الترخيص في GitHub، خصوصاً عندما يكون المستودع عاماً.

## تشغيل Windows للمطور

```powershell
git clone https://github.com/qadayas940-ui/ClinicDataSystem.git
cd ClinicDataSystem
git switch codex/v1-complete
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\init_db.py
python launcher.py
```

يفتح التطبيق محلياً على `http://127.0.0.1:8765`. في أول تشغيل ينشئ المالك حسابه بنفسه، ولا توجد كلمة مرور افتراضية داخل الكود.

## تخزين البيانات والتحديث

- ملفات البرنامج في مجلد التثبيت.
- قاعدة البيانات والمرفوعات والنسخ الاحتياطية في مسار يختاره المستخدم عند التثبيت.
- حذف البرنامج أو تثبيت تحديث لا يحذف مجلد البيانات.
- قبل ترحيلات قاعدة البيانات تؤخذ نسخة أمان تلقائية.
- عند التشغيل تؤخذ نسخة يومية بصيغة `.clinicbackup` إذا لم توجد نسخة خلال 24 ساعة.
- الاستعادة تتم والتطبيق متوقف:

```powershell
python manage.py restore_backup "C:\ClinicBackups\ClinicData-....clinicbackup" --confirm
```

## ملف Excel التاريخي

محرك التحليل يقرأ كل الأوراق والصفوف لا عينة منها، ويفهم التخطيط الخاص للأوراق الأربع. يحفظ الملف المؤرشف وبصمته، الصيغة الأصلية والقيمة المحسوبة، الورقة والصف، ثم يصنف كل سجل: جاهز، مراجعة، مانع، تكرار محتمل، أو زيارة متكررة محتملة. لا يجري دمج أو حذف تلقائي.

## بناء مثبت Windows

يُبنى المثبت تلقائياً عبر GitHub Actions من workflow باسم **Windows installer**. ويمكن بناؤه يدوياً على Windows:

```powershell
pip install -r requirements-build.txt
pyinstaller --clean --noconfirm ClinicDataSystem.spec
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\ClinicDataSystem.iss
```

الناتج في `release/ClinicDataSystem-Setup-1.1.0.exe`.

## الاختبارات

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python -m ruff check .
```

آخر تحقق: 25 اختباراً آلياً ناجحاً، بالإضافة إلى فحص كامل للمصنف الفعلي واكتشاف 50,146 سجل بيانات فعلياً من دون نشر أسماء المرضى.

## الشبكة

يمكن تفعيل الوصول داخل شبكة العيادة من شاشة «أجهزة العيادة»، ثم إعادة تشغيل البرنامج وفتح الرابط المعروض من الأجهزة الأخرى. لا تفتح منفذ التطبيق مباشرة على الإنترنت؛ الوصول الخارجي يحتاج VPN أو بوابة HTTPS موثوقة في مرحلة النشر.

راجع [سياسة الأمان](SECURITY.md) قبل إدخال أي بيانات تشغيلية.
