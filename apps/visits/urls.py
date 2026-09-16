from django.urls import path

from . import views

app_name = "visits"
urlpatterns = [
    path("", views.visit_list, name="list"),
    path("new/", views.visit_create, name="create"),
    path("new/<uuid:patient_id>/", views.visit_create, name="create_for_patient"),
    path("<int:pk>/edit/", views.visit_edit, name="edit"),
]
