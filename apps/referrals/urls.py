from django.urls import path

from . import views

app_name = "referrals"
urlpatterns = [path("", views.referral_list, name="list"), path("new/", views.referral_create, name="create"), path("new/<uuid:patient_id>/", views.referral_create, name="create_for_patient"), path("<int:pk>/edit/", views.referral_edit, name="edit")]
