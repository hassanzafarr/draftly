from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("verify-email/", views.verify_email, name="verify-email"),
    path("me/", views.me, name="me"),
    path("profile/", views.update_profile, name="update-profile"),
    path("password/", views.change_password, name="change-password"),
    path("org/", views.org_settings, name="org-settings"),
    path("password-reset/", views.password_reset_request, name="password-reset-request"),
    path("password-reset/confirm/", views.password_reset_confirm, name="password-reset-confirm"),
    path("google/", views.google_auth, name="google-auth"),
    path("google/complete/", views.google_auth_complete, name="google-auth-complete"),
]
