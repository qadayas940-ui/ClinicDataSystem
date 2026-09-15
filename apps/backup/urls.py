from django.urls import path

from . import views

app_name = "backup"
urlpatterns = [path("", views.backup_list, name="list"), path("create/", views.backup_create, name="create"), path("<int:pk>/download/", views.backup_download, name="download"), path("export/excel/", views.excel_export, name="excel_export")]
