from django.urls import path

from . import views

app_name = "importer"
urlpatterns = [path("", views.batch_list, name="list"), path("upload/", views.upload_workbook, name="upload"), path("batch/<int:pk>/", views.batch_detail, name="batch_detail"), path("row/<int:pk>/", views.row_detail, name="row_detail")]
