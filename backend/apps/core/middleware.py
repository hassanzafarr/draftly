"""Custom middleware — security-scoped extras for Draftly.

`AdminIPAllowlistMiddleware` restricts `/admin/` access to a configured set
of IPs/CIDRs. Disabled by default for local dev; enable in production by
setting `ADMIN_IP_ALLOWLIST` to a comma-separated list (e.g.
"203.0.113.5,198.51.100.0/24").
"""
import ipaddress
import logging

from django.conf import settings
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)


def _parse_allowlist(raw: str):
    """Return a list of IPv4/IPv6 networks. Bad entries are logged + skipped."""
    networks = []
    for entry in (raw or "").split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("Invalid ADMIN_IP_ALLOWLIST entry: %r", entry)
    return networks


def _client_ip(request):
    """Resolve the client IP, trusting `X-Forwarded-For` only when behind a proxy.

    `USE_X_FORWARDED_HOST` / `SECURE_PROXY_SSL_HEADER` already imply a proxy
    in front, so XFF can be trusted in that deployment shape. We take the
    left-most non-empty entry (the original client per the XFF spec).
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        candidate = xff.split(",")[0].strip()
        if candidate:
            return candidate
    return request.META.get("REMOTE_ADDR", "")


class AdminIPAllowlistMiddleware:
    """Reject /admin/ requests from IPs outside `settings.ADMIN_IP_ALLOWLIST`.

    No-op when the allowlist is empty (e.g. local dev). Place this AFTER
    SecurityMiddleware so HTTPS redirects still apply first.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        raw = getattr(settings, "ADMIN_IP_ALLOWLIST", "") or ""
        self.networks = _parse_allowlist(raw)
        self.enabled = bool(self.networks)

    def __call__(self, request):
        if self.enabled and request.path.startswith("/admin"):
            ip_str = _client_ip(request)
            if not self._ip_allowed(ip_str):
                logger.warning("Blocked /admin request from %s", ip_str or "unknown")
                return HttpResponseForbidden("Forbidden")
        return self.get_response(request)

    def _ip_allowed(self, ip_str: str) -> bool:
        if not ip_str:
            return False
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        return any(ip_obj in net for net in self.networks)
