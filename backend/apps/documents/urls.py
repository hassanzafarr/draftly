from django.urls import path

from . import views

urlpatterns = [
    path("", views.document_list, name="document-list"),
    path("events/", views.document_events, name="document-events"),
    path("<uuid:pk>/", views.document_detail, name="document-detail"),
]
