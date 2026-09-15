import hashlib
import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from apps.accounts.models import Role
from apps.core.models import LicenseState
from apps.importer.services import analyze_workbook
from apps.patients.models import Patient
from apps.patients.services import create_patient

User = get_user_model()


class PatientWorkflowTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name="المنظم", code=Role.CODE_ORGANIZER)
        self.user = User.objects.create_user(username="org", password="StrongPass123", role=self.role)

    def test_patient_gets_permanent_code_and_derived_age(self):
        patient = create_patient({"full_name": "اختبار مريض كامل", "gender": "male", "date_of_birth": timezone.localdate().replace(year=timezone.localdate().year - 20), "approx_age_value": None, "approx_age_unit": "", "phone": "0770 123 4567", "address": "الموصل"}, self.user)
        self.assertTrue(patient.internal_code.startswith("CLN-"))
        self.assertEqual(patient.display_name, "اختبار مريض كامل")
        self.assertIn("20", patient.calculated_age)
        self.assertEqual(patient.contacts.first().value, "07701234567")

    def test_search_by_name(self):
        patient = create_patient({"full_name": "سارة أحمد محمود", "gender": "female", "date_of_birth": None, "approx_age_value": 8, "approx_age_unit": "year", "phone": "", "address": "الزهور"}, self.user)
        self.client.force_login(self.user)
        response = self.client.get(reverse("patients:list"), {"q": "سارة"})
        self.assertContains(response, patient.internal_code)


class TrialSafetyTests(TestCase):
    def setUp(self):
        role = Role.objects.create(name="المالك", code=Role.CODE_OWNER)
        self.user = User.objects.create_user(username="owner", password="StrongPass123", role=role)
        self.client.force_login(self.user)
        LicenseState.objects.create(activation_date=timezone.now() - timedelta(days=31), trial_days=30, expires_at=timezone.now() - timedelta(days=1), is_trial=True, mode="trial")

    def test_expired_trial_is_read_only_not_data_deletion(self):
        response = self.client.post(reverse("patients:create"), {"full_name": "لن ينشأ", "gender": "unknown"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(self.client.get(reverse("patients:list")).status_code, 200)


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
