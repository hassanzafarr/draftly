"""Custom middleware — security-scoped extras for Draftly.

`AdminIPAllowlistMiddleware` restricts `/admin/` access to a configured set
of IPs/CIDRs. Disabled by default for local dev; enable in production by
setting `ADMIN_IP_ALLOWLIST` to a comma-separated list (e.g.
"203.0.113.5,198.51.100.0/24").
"""

import ipaddress
import logging
import time
import uuid

from django.conf import settings
from django.http import HttpResponseForbidden

from .logging import reset_logging_context, set_logging_context

logger = logging.getLogger(__name__)
request_logger = logging.getLogger("apps.core.request")


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


class RequestLogMiddleware:
    """Emit a structured completion log for every HTTP request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        client_ip = _client_ip(request) or request.META.get("REMOTE_ADDR", "")
        token = set_logging_context(
            request_id=request_id,
            http_method=request.method,
            http_path=request.path,
            client_ip=client_ip,
        )
        request.request_id = request_id
        started_at = time.monotonic()

        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            request_logger.exception(
                "HTTP request failed",
                extra={
                    "event": "http_request_failed",
                    "request_id": request_id,
                    "http_method": request.method,
                    "http_path": request.path,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    **_user_context(request),
                },
            )
            raise
        else:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            response["X-Request-ID"] = request_id
            status_code = getattr(response, "status_code", None)
            level = logging.WARNING if status_code and status_code >= 500 else logging.INFO
            request_logger.log(
                level,
                "HTTP request completed",
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "http_method": request.method,
                    "http_path": request.path,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    **_user_context(request),
                },
            )
            return response
        finally:
            reset_logging_context(token)


def _user_context(request):
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return {}

    context = {"user_id": str(getattr(user, "id", ""))}
    org_id = getattr(user, "org_id", "")
    if org_id:
        context["org_id"] = str(org_id)
    return context
