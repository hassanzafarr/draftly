from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("me/", views.me, name="me"),
    path("profile/", views.update_profile, name="update-profile"),
    path("password/", views.change_password, name="change-password"),
    path("org/", views.org_settings, name="org-settings"),
]
