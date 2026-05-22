from django.urls import path
from . import views

urlpatterns = [
    path("checkout/", views.create_checkout_session, name="billing_checkout"),
    path("portal/", views.create_portal_session, name="billing_portal"),
    path("subscription/", views.subscription_status, name="billing_subscription"),
    path("webhook/", views.stripe_webhook, name="billing_webhook"),
]
