from django.urls import path

from . import views

urlpatterns = [
    path("rfps/", views.rfp_list, name="rfp-list"),
    path("rfps/<uuid:pk>/", views.rfp_detail, name="rfp-detail"),
    path("rfps/<uuid:rfp_pk>/generate/", views.generate_proposal, name="generate-proposal"),
    path("proposals/", views.proposal_list, name="proposal-list"),
    path("proposals/<uuid:pk>/", views.proposal_detail, name="proposal-detail"),
    path("proposals/<uuid:pk>/events/", views.proposal_events, name="proposal-events"),
    path(
        "proposals/<uuid:pk>/export/docx/", views.proposal_export_docx, name="proposal-export-docx"
    ),
    path("templates/", views.template_list, name="template-list"),
    path("templates/<uuid:pk>/", views.template_detail, name="template-detail"),
    path("metrics/generation/", views.generation_metrics, name="generation-metrics"),
    path("analytics/stats/", views.analytics_stats, name="analytics-stats"),
]
