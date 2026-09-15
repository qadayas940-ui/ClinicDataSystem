from django.urls import path

from . import views

app_name = "laboratory"
urlpatterns = [path("", views.order_list, name="list"), path("new/", views.order_create, name="create"), path("new/<uuid:patient_id>/", views.order_create, name="create_for_patient")]
