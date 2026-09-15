from django.urls import path

from . import views

app_name = "updater"
urlpatterns = [path("", views.update_list, name="list"), path("check/", views.update_check, name="check")]
