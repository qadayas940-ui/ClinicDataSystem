import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from openpyxl import Workbook, load_workbook

from apps.accounts.models import Role
from apps.core.models import Department, Notification, ReferenceValue
from apps.importer.services import analyze_workbook, import_batch_records
from apps.patients.forms import PatientForm
from apps.patients.models import Patient
from apps.patients.services import create_patient, find_patient_candidates
from apps.visits.models import Visit

User = get_user_model()


class PatientWorkflowTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name="المنظم", code=Role.CODE_ORGANIZER)
        self.user = User.objects.create_user(username="org", password="StrongPass123", role=self.role)

    def test_patient_gets_permanent_code_and_derived_age(self):
        patient = create_patient({"full_name": "اختبار مريض كامل علي", "gender": "male", "date_of_birth": timezone.localdate().replace(year=timezone.localdate().year - 20), "approx_age_value": None, "approx_age_unit": "", "phone": "0770 123 4567", "address": "الموصل"}, self.user)
        self.assertRegex(patient.internal_code, rf"^CLN{str(timezone.localdate().year)[-2:]}-\d{{10}}$")
        self.assertEqual(patient.display_name, "اختبار مريض كامل علي")
        self.assertIn("20", patient.calculated_age)
        self.assertEqual(patient.contacts.first().value, "+9647701234567")

    def test_search_by_name(self):
        patient = create_patient({"full_name": "سارة أحمد محمود علي", "gender": "female", "date_of_birth": None, "approx_age_value": 8, "approx_age_unit": "year", "phone": "07899189225", "address": "الزهور"}, self.user)
        self.client.force_login(self.user)
        response = self.client.get(reverse("patients:list"), {"q": "سارة"})
        self.assertContains(response, patient.internal_code)

    def test_unified_search_and_match_find_manual_or_imported_patient(self):
        manual = create_patient({"full_name": "سارة أحمد محمود علي", "gender": "female", "date_of_birth": None, "approx_age_value": 8, "approx_age_unit": "year", "phone": "07899189225", "address": "الزهور"}, self.user)
        imported = create_patient({"full_name": "حيدر سالم كاظم حسن", "gender": "male", "date_of_birth": None, "approx_age_value": 32, "approx_age_unit": "year", "phone": "07701234567", "address": "الموصل"}, self.user)
        imported.source_type = "excel"
        imported.external_id = "XLS-TEST-1"
        imported.save(update_fields=["source_type", "external_id", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("patients:list"), {"phone": "07701234567", "age": "32"})
        self.assertContains(response, imported.internal_code)
        self.assertNotContains(response, manual.internal_code)
        self.assertContains(response, "السجل المستورد")

        response = self.client.get(reverse("patients:match"), {"name": "حيدر سالم", "phone": "07701234567", "age": "32"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["id"], str(imported.pk))
        self.assertEqual(response.json()["results"][0]["source"], "مستورد")

    def test_doctor_choices_depend_on_department(self):
        women = Department.objects.create(name="نسائية", code="WOMEN")
        children = Department.objects.create(name="اطفال", code="CHILDREN")
        doctor_women = ReferenceValue.objects.create(category="doctor", canonical_name="د. طبيبة نسائية", normalized_name="د طبيبه نسائيه")
        doctor_children = ReferenceValue.objects.create(category="doctor", canonical_name="د. طبيب أطفال", normalized_name="د طبيب اطفال")
        doctor_women.departments.add(women)
        doctor_children.departments.add(children)
        form = PatientForm(department=women)
        self.assertEqual(list(form.fields["doctor_reference"].queryset), [doctor_women])

    def test_patient_drawer_uses_same_screen_data(self):
        patient = create_patient({"full_name": "سارة أحمد محمود علي", "gender": "female", "date_of_birth": None, "approx_age_value": 8, "approx_age_unit": "year", "phone": "07899189225", "address": "الزهور"}, self.user)
        self.client.force_login(self.user)
        response = self.client.get(reverse("patients:drawer", args=[patient.pk]))
        self.assertContains(response, "بطاقة المريض")
        self.assertContains(response, patient.internal_code)

    def test_patient_drawer_saves_without_server_error(self):
        patient = create_patient({"full_name": "سارة أحمد محمود علي", "gender": "female", "date_of_birth": None, "approx_age_value": 8, "approx_age_unit": "year", "phone": "07899189225", "address": "الزهور"}, self.user)
        self.client.force_login(self.user)
        response = self.client.post(reverse("patients:drawer", args=[patient.pk]), {
            "full_name": "سارة أحمد محمود حسن", "gender": "female",
            "approx_age_value": "9", "approx_age_unit": "year",
            "phone": "07899189225", "address": "الزهور",
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        patient.refresh_from_db()
        self.assertEqual(patient.display_name, "سارة أحمد محمود حسن")

    def test_live_search_from_first_character_name_phone_and_id(self):
        patient = create_patient({"full_name": "محمد أحمد علي حسن", "gender": "male", "date_of_birth": None, "approx_age_value": 30, "approx_age_unit": "year", "phone": "07701234567", "address": "الموصل"}, self.user)
        self.client.force_login(self.user)
        for query in ("م", "محمد", "701234", patient.internal_code):
            response = self.client.get(reverse("patients:search"), {"q": query})
            self.assertEqual(response.status_code, 200)
            self.assertIn(str(patient.pk), [item["id"] for item in response.json()["results"]])

    def test_duplicate_candidates_are_safe_and_confirmed_patient_gets_visit(self):
        existing = create_patient({"full_name": "محمد أحمد علي حسن", "gender": "male", "date_of_birth": None, "approx_age_value": 30, "approx_age_unit": "year", "phone": "07701234567", "address": "الموصل"}, self.user)
        self.assertFalse(find_patient_candidates(name="شخص جديد تماماً", phone="07800000000"))
        self.assertEqual(find_patient_candidates(name="محمد أحمد علي حسن", phone="07701234567")[0]["patient"], existing)
        uncertain = find_patient_candidates(name="محمد أحمد علي حسن", phone="07899999999", gender="female", address="البصرة")
        self.assertEqual(uncertain[0]["reasons"], ["الاسم مطابق"])
        self.assertLess(uncertain[0]["score"], 50)  # مرشح بشري فقط، وليس دمجاً تلقائياً

        self.client.force_login(self.user)
        before = Patient.objects.count()
        visit_url = reverse("visits:create_for_patient", args=[existing.pk])
        response = self.client.post(visit_url, {
            "patient_code": existing.internal_code,
            "visit_date": "2026-09-16T10:00", "visit_type": "follow_up", "status": "open",
            "chief_complaint": "متابعة", "diagnosis": "فحص دوري", "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patient.objects.count(), before)
        self.assertTrue(Visit.objects.filter(patient=existing, chief_complaint="متابعة").exists())

    def test_notifications_open_and_mark_all_read_without_deleting(self):
        patient = create_patient({"full_name": "اختبار إشعار مريض علي", "gender": "male", "date_of_birth": None, "approx_age_value": 20, "approx_age_unit": "year", "phone": "07701111111", "address": "الموصل"}, self.user)
        first = Notification.objects.create(user=self.user, title="الأول", target_url=reverse("patients:list") + f"?patient={patient.pk}")
        Notification.objects.create(user=self.user, title="الثاني")
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:notification_open", args=[first.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.json()["unread"], 1)
        first.refresh_from_db(); self.assertIsNotNone(first.read_at)
        response = self.client.post(reverse("core:notifications"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.json()["unread"], 0)
        self.assertEqual(Notification.objects.count(), 2)


class ImportAnalysisTests(TestCase):
    def _workbook(self, path):
        book = Workbook()
        review = book.active; review.title = "مراجعة المرضى"
        review.append(["عنوان"]); review.append([]); review.append(["ت", "الاسم", "الجنس", "العمر", "العنوان", "رقم الهاتف", "عدد التكرار", "القسم", "الحالة", "اسم الطبيب", "اسم المنظم", "التاريخ", "الملاحظات"])
        review.append([1, "علي حسن كامل", "ذكر", 30, "الموصل", "07701234567", 2, "عام", "مراجعة", "د. أ", "منظم", "2026-01-01", ""])
        review.append([2, "علي حسن كامل", "ذكر", 31, "الموصل", "07701234567", 2, "عام", "متابعة", "د. أ", "منظم", "2026-02-01", ""])
        review.append(["=ROW()-3", None, None, None, None, None, "=COUNTIF(B:B,B6)"])
        lab = book.create_sheet("المختبر"); lab.append(["مختبر"]); lab.append(["الاسم", None, "العمر", "نوع الفحص"]); lab.append([1, "نور سامي", 22, "CBC"])
        referrals = book.create_sheet("احالات"); referrals.append(["عنوان"]); referrals.append(["الاسم", None, "الطبيب"]); referrals.append([1, "هدى ياسين", "د. عيون"])
        eye = book.create_sheet("عيادة العيون"); eye.append(["الاسم", None, "العمر", "الجنس", "المنطقة"]); eye.append([1, "سعد وليد", 9, "ذكر", "الرفاعي"])
        book.save(path)

    def test_four_sheet_profiles_skip_formula_counter_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "patients.xlsx"; self._workbook(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            batch, created = analyze_workbook(path, digest, path.name, None)
        self.assertTrue(created)
        self.assertEqual(batch.total_rows, 5)
        self.assertEqual(list(batch.sheets.values_list("actual_data_rows", flat=True)), [2, 1, 1, 1])
        self.assertEqual(batch.rows.filter(classification="repeat_visit").count(), 1)
        self.assertTrue(ReferenceValue.objects.filter(category="department", canonical_name="عام").exists())
        self.assertTrue(ReferenceValue.objects.filter(category="lab_test", canonical_name="CBC").exists())
        self.assertTrue(ReferenceValue.objects.filter(category="referral_destination").exists())
        self.assertEqual(batch.rows.filter(raw_data__source__isnull=False).count(), 5)
        imported = import_batch_records(batch, None)
        self.assertGreaterEqual(imported, 1)
        imported_patient = Patient.objects.filter(source_type="excel").first()
        self.assertIsNotNone(imported_patient)
        self.assertEqual(imported_patient.source_file, "patients.xlsx")
        self.assertIn("source_columns", imported_patient.additional_data)
        self.assertEqual(Patient.objects.filter(names__full_name="علي حسن كامل").count(), 1)
        self.assertEqual(Patient.objects.get(names__full_name="علي حسن كامل").visits.count(), 2)
        imported_patient = Patient.objects.get(names__full_name="علي حسن كامل")
        self.assertEqual(imported_patient.imported_visit_count, 2)
        self.assertEqual(imported_patient.total_visit_count, 2)

    def test_imported_registry_opens_every_imported_patient_drawer(self):
        role = Role.objects.create(name="مدقق", code=Role.CODE_AUDITOR)
        user = User.objects.create_user(username="auditor", password="StrongPass123", role=role)
        patient = create_patient({"full_name": "مريض مستورد كامل علي", "gender": "male", "approx_age_value": 41, "approx_age_unit": "year", "phone": "07701234568", "address": "الموصل"}, user)
        patient.source_type = "excel"
        patient.source_sheet = "مراجعة المرضى"
        patient.source_row = 51
        patient.save(update_fields=["source_type", "source_sheet", "source_row", "updated_at"])
        self.client.force_login(user)
        response = self.client.get(reverse("patients:imported"))
        self.assertContains(response, patient.internal_code)
        response = self.client.get(reverse("patients:drawer", args=[patient.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "بطاقة المريض")

    def test_gender_variants_are_normalized_without_blocking(self):
        from apps.importer.services import GENDERS, normalize_arabic

        for raw, expected in (("رجل", "male"), ("Male", "male"), ("امرأة", "female"), ("F", "female")):
            self.assertEqual(GENDERS[normalize_arabic(raw)], expected)


class BackupExportTests(TestCase):
    def setUp(self):
        role = Role.objects.create(name="المالك", code=Role.CODE_OWNER)
        self.user = User.objects.create_user(username="owner-export", password="StrongPass123", role=role)
        self.patient = create_patient({"full_name": "مريض تصدير كامل علي", "gender": "male", "approx_age_value": 35, "approx_age_unit": "year", "phone": "07705555555", "address": "الموصل"}, self.user)
        self.client.force_login(self.user)

    def _download(self, route):
        response = self.client.get(reverse(route))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        return b"".join(response.streaming_content)

    def test_excel_csv_and_json_are_real_downloads(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(DATA_PATH=Path(directory)):
            excel = self._download("backup:excel_export")
            workbook = load_workbook(io.BytesIO(excel), read_only=True)
            self.assertIn("المرضى", workbook.sheetnames)
            self.assertGreaterEqual(sum(1 for _ in workbook["المرضى"].iter_rows(values_only=True)), 2)
            workbook.close()

            csv_archive = self._download("backup:csv_export")
            with zipfile.ZipFile(io.BytesIO(csv_archive)) as archive:
                self.assertIn("المرضى.csv", archive.namelist())

            json_data = json.loads(self._download("backup:json_export").decode("utf-8"))
            self.assertEqual(json_data["المرضى"][0]["الرقم"], self.patient.internal_code)
