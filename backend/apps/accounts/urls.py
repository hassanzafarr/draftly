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
    path("team/members/", views.team_members, name="team-members"),
    path("team/members/<uuid:pk>/", views.team_member_detail, name="team-member-detail"),
    path("team/invites/", views.team_invites, name="team-invites"),
    path("team/invites/<uuid:pk>/", views.team_invite_detail, name="team-invite-detail"),
    # `accept/` must precede the catch-all token route
    path("invites/accept/", views.invite_accept, name="invite-accept"),
    path("invites/<str:token>/", views.invite_info, name="invite-info"),
]
