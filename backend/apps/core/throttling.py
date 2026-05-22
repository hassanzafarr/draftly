"""Scoped throttle subclasses for function-based views.

`@api_view` does not propagate a `throttle_scope` attribute to the wrapping
view class, so `ScopedRateThrottle` cannot resolve the scope dynamically.
Each subclass below pins its scope at class level.

Rates are defined in `settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.
"""
from rest_framework.throttling import ScopedRateThrottle


class _PinnedScopeThrottle(ScopedRateThrottle):
    """Base — sets `self.scope` from a class attribute instead of the view."""
    scope_name = ""

    def allow_request(self, request, view):
        self.scope = self.scope_name
        # If the scope isn't configured (e.g. in tests), allow through.
        if self.scope not in self.THROTTLE_RATES:
            return True
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super(ScopedRateThrottle, self).allow_request(request, view)


class AuthLoginThrottle(_PinnedScopeThrottle):
    scope_name = "auth_login"


class AuthRegisterThrottle(_PinnedScopeThrottle):
    scope_name = "auth_register"


class PasswordChangeThrottle(_PinnedScopeThrottle):
    scope_name = "password_change"


class ProposalGenerateThrottle(_PinnedScopeThrottle):
    scope_name = "proposal_generate"


class DocumentUploadThrottle(_PinnedScopeThrottle):
    """Only throttles POST — GET list polling stays on default user rate."""
    scope_name = "document_upload"

    def allow_request(self, request, view):
        if request.method != "POST":
            return True
        return super().allow_request(request, view)


class BillingCheckoutThrottle(_PinnedScopeThrottle):
    scope_name = "billing_checkout"
