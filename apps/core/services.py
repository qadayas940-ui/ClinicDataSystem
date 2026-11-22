"""خدمات تشغيلية آمنة لنظام العيادة."""
from django.db import transaction


@transaction.atomic
def reset_clinic_data():
    """إفراغ سجلات العيادة مع إبقاء مخطط القاعدة والحسابات والنسخ الاحتياطية.

    تُحذف بيانات المرضى والزيارات والمختبر والإحالات والاستيراد والقوائم
    المرجعية والأقسام. لا تُحذف جداول النظام أو المستخدمون أو الصلاحيات.
    """
    from apps.core.models import Department, Notification, ReferenceValue
    from apps.eyeclinic.models import EyeClinicVisit
    from apps.importer.models import (
        DataIssue, ImportBatch, ImportFile, ImportSheet, MatchCandidate,
        MergeDecision, ReviewDecision, SourceRow,
    )
    from apps.laboratory.models import LabOrder, LabOrderTest
    from apps.patients.models import (
        Patient, PatientAddress, PatientContact, PatientName, PatientSequence,
    )
    from apps.referrals.models import Referral, ReferralFollowup
    from apps.visits.models import Visit, VisitService

    deleted = {}
    def remove(label, qs):
        deleted[label] = qs.count()
        qs.delete()

    # الجداول التابعة أولاً لتفادي قيود PROTECT/العلاقات المتداخلة.
    remove("merge_decisions", MergeDecision.objects.all())
    remove("match_candidates", MatchCandidate.objects.all())
    remove("review_decisions", ReviewDecision.objects.all())
    remove("data_issues", DataIssue.objects.all())
    remove("source_rows", SourceRow.objects.all())
    remove("import_sheets", ImportSheet.objects.all())
    remove("import_files", ImportFile.objects.all())
    remove("import_batches", ImportBatch.all_objects.all())

    remove("referral_followups", ReferralFollowup.objects.all())
    remove("referrals", Referral.objects.all())
    remove("lab_tests", LabOrderTest.objects.all())
    remove("lab_orders", LabOrder.objects.all())
    remove("visit_services", VisitService.objects.all())
    remove("visits", Visit.objects.all())
    remove("eye_visits", EyeClinicVisit.objects.all())

    remove("patient_addresses", PatientAddress.objects.all())
    remove("patient_contacts", PatientContact.objects.all())
    remove("patient_names", PatientName.objects.all())
    remove("patients", Patient.all_objects.all())
    remove("patient_sequence", PatientSequence.objects.all())

    remove("notifications", Notification.objects.all())
    remove("references", ReferenceValue.all_objects.all())
    remove("departments", Department.all_objects.all())
    return deleted
