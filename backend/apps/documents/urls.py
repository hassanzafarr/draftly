from django.urls import path
from . import views

urlpatterns = [
    path("", views.document_list, name="document-list"),
    path("<uuid:pk>/", views.document_detail, name="document-detail"),
]
