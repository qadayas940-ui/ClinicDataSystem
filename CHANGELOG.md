## 1.5.7

- Made repeated startup responsive by running only pending migrations synchronously and moving import repair and daily backup to background maintenance.
- Rebuilt Excel exports with patient names instead of database IDs, the requested Arabic column order, native Excel tables, filters, sorting, frozen headers, and right-to-left worksheets.
- Made phone, address, and diagnosis optional; accepted two-part names; and added a read-only live calculated-age field next to date of birth.
- Exposed safe soft-delete and restore actions for patients, visits, laboratory orders, referrals, and eye-clinic visits through the unified trash.
- Kept new manual records and old imported batches separate so they can be reviewed and merged later inside the same application.

## 1.5.6

- Added a production Render Blueprint with a private managed PostgreSQL database, persistent application storage, HTTPS-only cookies, health checks, and automatic deploys from `codex/v1-5-build`.
- Accept Render's generated public HTTPS URL automatically while preserving an explicitly configured `PUBLIC_BASE_URL`.
- Corrected the Windows D-drive build helper to use the supported release branch.

# سجل التغييرات

## [1.4.0] — بطاقات الاستيراد الكاملة وزر الرجوع

- إصلاح خطأ 500 عند فتح صفوف Excel التي لا تحتوي حقل الحالة أو التشخيص.
- ربط كل التصنيفات التي تحتوي اسماً: الجاهز والمراجعة والمانع والتكرار والزيارة المحتملة.
- فتح ملف المريض مباشرة من تقرير الاستيراد وإتاحة إكمال معلوماته أو إضافة السجل غير المرتبط.
- توحيد بطاقات Excel المكررة حسب الاسم المطبّع مع نقل الزيارات والمختبر والإحالات والعيون إلى البطاقة الدائمة الأقدم.
- إضافة زر رجوع ثابت في الشريط العلوي لكل شاشات النظام.

## [1.3.1] — منع تعارض تشغيل قاعدة البيانات

- منع أكثر من عملية محلية من تنفيذ الترحيلات وإصلاح البيانات على SQLite في الوقت نفسه.
- جعل نافذة البرنامج التي يفتحها المثبّت تنتظر الخادم التلقائي بدلاً من منافسته على قاعدة البيانات.
- عند فتح اختصار البرنامج والخادم يعمل، تُفتح الواجهة نفسها دون تشغيل خادم ثانٍ.

## [1.3.0] — إصلاح بيانات Excel والتحرير والشبكة المحلية

- تصحيح عدد المراجعات من القيمة المحسوبة في Excel بدلاً من رقم الصف داخل صيغة COUNTIF.
- ربط الصفوف التاريخية غير المرتبطة وإظهار السجلات والخدمات من جميع أوراق الاستيراد.
- إضافة تعديل مستقل لطلبات المختبر والإحالات مع تعديل ملف المريض.
- تشغيل الخادم على الشبكة المحلية وفتح TCP/8765 لجميع ملفات تعريف جدار الحماية.
- تحسين وضوح الشعار وتمييز بطاقة لوحة العمل.

جميع التغييرات المهمة في هذا المشروع تُوثّق في هذا الملف.

## [1.2.0] — السجل المستورد والشبكة والتصدير الفعلي

### أُضيف وصُحح
- قسم مستقل للسجل المستورد مع بطاقة المريض الموحدة.
- حفظ عدد المراجعات التاريخية من Excel وعرضه مع سجل الزيارات.
- تنزيل Excel وCSV ZIP وJSON والنسخة الكاملة فعلياً.
- مشاركة الشبكة المحلية وفتح منفذ الخادم عبر Windows Firewall.
- كشف المريض المحتمل أثناء التسجيل وخيارات التعديل أو إضافة زيارة.
- تعديل الزيارة وبطاقات الأقسام والأطباء الفعليين.

## [1.1.0] — واجهة المرضى والاستيراد الكامل

### أُضيف
- واجهة قائمة المرضى بالشريط الجانبي والبطاقة المنزلقة داخل الشاشة مع RTL/LTR فعلي.
- معرّف خارجي وبيانات مصدر Excel وحقول إضافية لا تفقد الأعمدة غير المعروفة.
- ربط الأطباء المرجعيين بالأقسام المستخرجة من Excel وقوائم تابعة للقسم.
- مطابقة أعمدة Excel، إدراج السجلات الجاهزة، وإضافة سجل واحد بعد مراجعته.
- إشعارات حقيقية لأحداث المرضى والاستيراد، وشعار العيادة المستخرج من المصنف.
- أيقونة Windows ومثبت الإصدار 1.1.0 وسكربت بناء يمنع تشغيل النسخة القديمة.

## [1.0.0] — المرحلة 1

### أُضيف
- هيكل المشروع الكامل (Django + إعدادات base/development/testing/production).
- نماذج قاعدة البيانات لجميع التطبيقات (core, accounts, patients, visits,
  laboratory, referrals, ophthalmology, importer, backup, updater).
- نظام الحسابات والصلاحيات: مستخدم مخصص، أدوار (مالك/طبيب/منظم/مدقق)،
  تسجيل دخول عربي، قفل بعد 5 محاولات فاشلة، إجبار تغيير كلمة المرور المؤقتة.
- وسيط تسجيل التدقيق (Audit Log) دون بيانات حساسة.
- واجهة برمجية لفحص الصحة `GET /api/health/`.
- الشاشة الرئيسية (Dashboard) وشاشة فحص الصحة.
- قوالب عربية RTL (Bootstrap RTL + خط Tajawal + HTMX).
- مشغّل سطح المكتب (Waitress + pywebview) وسكربتات الإعداد.
- اختبارات النماذج والمصادقة وفحص الصحة.
