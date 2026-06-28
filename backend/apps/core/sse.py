"""Server-Sent Events helpers.

The app has no ASGI/channels stack, so SSE is implemented as a
StreamingHttpResponse whose generator polls the database server-side and emits
an event only when the watched state changes. This moves the 2-5s HTTP polling
loop off the network: one connection per generation instead of a request every
few seconds.

Constraints baked into `stream_changes`:
- Streams are capped at SSE_MAX_DURATION_SECONDS (must stay under the gunicorn
  worker timeout); the client reconnects on `event: timeout`.
- `close_old_connections()` runs each tick so long-lived streams don't hold a
  stale DB connection past CONN_MAX_AGE.
- A `: keep-alive` comment is sent every SSE_HEARTBEAT_SECONDS so proxies
  (Azure Container Apps ingress, Vite dev proxy) don't drop the idle socket.
"""

import json
import time
from collections.abc import Callable, Iterator

from django.conf import settings
from django.db import close_old_connections, connection
from django.http import StreamingHttpResponse
from rest_framework.renderers import BaseRenderer


class ServerSentEventRenderer(BaseRenderer):
    """Lets DRF content negotiation pass for text/event-stream requests."""

    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def format_sse(data: dict | None = None, event: str | None = None) -> str:
    lines = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data or {})}")
    return "\n".join(lines) + "\n\n"


def stream_changes(
    fetch_state: Callable[[], dict | None],
    is_terminal: Callable[[dict], bool],
) -> Iterator[str]:
    """Yield an SSE `status` event whenever `fetch_state()` changes.

    Ends with `event: done` once `is_terminal(state)` is true, `event: gone` if
    `fetch_state()` returns None (row deleted), or `event: timeout` when the
    stream hits its duration cap while the state is still in flight.
    """
    poll_interval = settings.SSE_POLL_INTERVAL_SECONDS
    heartbeat = settings.SSE_HEARTBEAT_SECONDS
    deadline = time.monotonic() + settings.SSE_MAX_DURATION_SECONDS
    last_state = None
    last_beat = time.monotonic()

    while True:
        # Never recycle the connection mid-transaction. Outside a transaction
        # (normal request path) this reclaims connections past CONN_MAX_AGE;
        # inside one (e.g. ATOMIC_REQUESTS or the per-test transaction) calling
        # close_old_connections() would force-close the shared connection
        # because autocommit is off, breaking the caller and later reuse.
        if not connection.in_atomic_block:
            close_old_connections()
        state = fetch_state()
        if state is None:
            yield format_sse(event="gone")
            return
        if state != last_state:
            last_state = state
            last_beat = time.monotonic()
            yield format_sse(state, event="status")
        if is_terminal(state):
            yield format_sse(event="done")
            return

        now = time.monotonic()
        if now >= deadline:
            yield format_sse(event="timeout")
            return
        if now - last_beat >= heartbeat:
            last_beat = now
            yield ": keep-alive\n\n"
        time.sleep(poll_interval)


def sse_response(stream: Iterator[str]) -> StreamingHttpResponse:
    response = StreamingHttpResponse(stream, content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    # Tell buffering reverse proxies (nginx and compatibles) to pass events through.
    response["X-Accel-Buffering"] = "no"
    return response
