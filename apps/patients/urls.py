from django.urls import path

from . import views

app_name = "patients"

urlpatterns = [
    path("", views.patient_list, name="list"),
    path("new/", views.patient_create, name="create"),
    path("api/doctors/", views.doctors_for_department, name="doctors_for_department"),
    path("<uuid:pk>/drawer/", views.patient_drawer, name="drawer"),
    path("<uuid:pk>/", views.patient_detail, name="detail"),
    path("<uuid:pk>/edit/", views.patient_edit, name="edit"),
    path("<uuid:pk>/archive/", views.patient_archive, name="archive"),
    path("<uuid:pk>/qr/", views.patient_qr, name="qr"),
]
