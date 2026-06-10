import json
import logging
import sys

from apps.core.logging import JsonFormatter, reset_logging_context, set_logging_context


def test_json_formatter_emits_searchable_fields():
    formatter = JsonFormatter(service="draftly-test", environment="test")
    token = set_logging_context(request_id="req_123", http_path="/api/health/")
    try:
        record = logging.LogRecord(
            "apps.core.test",
            logging.INFO,
            __file__,
            12,
            "Processed org %s",
            ("org_123",),
            None,
            "test_func",
        )
        record.org_id = "org_123"
        record.duration_ms = 42

        payload = json.loads(formatter.format(record))
    finally:
        reset_logging_context(token)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "apps.core.test"
    assert payload["message"] == "Processed org org_123"
    assert payload["service"] == "draftly-test"
    assert payload["environment"] == "test"
    assert payload["request_id"] == "req_123"
    assert payload["http_path"] == "/api/health/"
    assert payload["org_id"] == "org_123"
    assert payload["duration_ms"] == 42


def test_json_formatter_includes_exception_details():
    formatter = JsonFormatter(service="draftly-test", environment="test")
    try:
        raise ValueError("bad input")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        "apps.core.test",
        logging.ERROR,
        __file__,
        34,
        "Failed",
        (),
        exc_info,
        "test_func",
    )

    payload = json.loads(formatter.format(record))

    assert payload["exception"]["type"] == "ValueError"
    assert payload["exception"]["message"] == "bad input"
    assert "ValueError: bad input" in payload["exception"]["stacktrace"]


def test_request_log_middleware_sets_request_id_header(api_client):
    response = api_client.get("/api/health/", HTTP_X_REQUEST_ID="req-test")

    assert response.status_code == 200
    assert response["X-Request-ID"] == "req-test"
