from django.urls import path

from . import views

app_name = "patients"

urlpatterns = [
    path("", views.patient_list, name="list"),
    path("imported/", views.imported_patient_list, name="imported"),
    path("new/", views.patient_create, name="create"),
    path("trash/", views.patient_trash, name="trash"),
    path("trash/<uuid:pk>/restore/", views.patient_restore, name="restore"),
    path("api/doctors/", views.doctors_for_department, name="doctors_for_department"),
    path("api/search/", views.patient_search, name="search"),
    path("api/changes/", views.patient_changes, name="changes"),
    path("api/match/", views.patient_match, name="match"),
    path("<uuid:pk>/drawer/", views.patient_drawer, name="drawer"),
    path("<uuid:pk>/", views.patient_detail, name="detail"),
    path("<uuid:pk>/edit/", views.patient_edit, name="edit"),
    path("<uuid:pk>/archive/", views.patient_archive, name="archive"),
    path("<uuid:pk>/qr/", views.patient_qr, name="qr"),
]
