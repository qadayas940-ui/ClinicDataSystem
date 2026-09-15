from django.urls import path

from . import views

app_name = "ophthalmology"
urlpatterns = [path("", views.eye_visit_list, name="list"), path("new/", views.eye_visit_create, name="create"), path("new/<uuid:patient_id>/", views.eye_visit_create, name="create_for_patient")]
