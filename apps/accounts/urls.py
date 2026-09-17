"""مسارات تطبيق الحسابات."""
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("setup-owner/", views.setup_owner, name="setup_owner"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password, name="change_password"),
    path("profile/", views.profile, name="profile"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
]
