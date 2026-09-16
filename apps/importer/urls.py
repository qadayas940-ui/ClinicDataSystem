from django.urls import path

from . import views

app_name = "importer"
urlpatterns = [
    path("", views.batch_list, name="list"),
    path("upload/", views.upload_workbook, name="upload"),
    path("batch/<int:pk>/", views.batch_detail, name="batch_detail"),
    path("batch/<int:pk>/commit/", views.commit_batch, name="commit_batch"),
    path("sheet/<int:pk>/mapping/", views.sheet_mapping, name="sheet_mapping"),
    path("row/<int:pk>/", views.row_detail, name="row_detail"),
    path("row/<int:pk>/commit/", views.commit_row, name="commit_row"),
]
