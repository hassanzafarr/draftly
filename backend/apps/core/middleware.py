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
    """Resolve the client IP for IP-allowlist checks.

    XFF is attacker-controllable on the way in — proxies *append* to it, they
    do not overwrite. To pick the real client we must count back from the
    right by the number of trusted hops in front of Django. The left-most
    entry is whatever the original client sent and must never be trusted.

    Config: `ADMIN_TRUSTED_PROXY_COUNT` (int, default 0).
      * 0 — no proxy in front; use `REMOTE_ADDR` and ignore XFF entirely.
      * N — exactly N trusted proxies (e.g. Railway edge = 1). The client IP
        is `xff[-N]`. If XFF has fewer than N entries the request is
        considered untrusted and "" is returned (deny).
    """
    trusted_count = int(getattr(settings, "ADMIN_TRUSTED_PROXY_COUNT", 0) or 0)
    remote_addr = request.META.get("REMOTE_ADDR", "")

    if trusted_count <= 0:
        return remote_addr

    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not xff:
        # Behind a proxy but no XFF — either a direct hit bypassing the proxy
        # or a misconfigured proxy. Either way, do not trust REMOTE_ADDR.
        return ""

    parts = [p.strip() for p in xff.split(",") if p.strip()]
    if len(parts) < trusted_count:
        # Fewer hops than expected → header shape doesn't match deployment.
        return ""
    return parts[-trusted_count]


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
