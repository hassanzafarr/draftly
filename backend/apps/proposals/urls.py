from django.urls import path
from . import views

urlpatterns = [
    path("rfps/", views.rfp_list, name="rfp-list"),
    path("rfps/<uuid:pk>/", views.rfp_detail, name="rfp-detail"),
    path("rfps/<uuid:rfp_pk>/generate/", views.generate_proposal, name="generate-proposal"),
    path("proposals/", views.proposal_list, name="proposal-list"),
    path("proposals/<uuid:pk>/", views.proposal_detail, name="proposal-detail"),
]
