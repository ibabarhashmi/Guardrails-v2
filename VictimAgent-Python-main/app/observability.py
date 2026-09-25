"""Logging and request tracing. Secrets and prompt bodies never logged."""

import logging
import re
import sys
import uuid

_KEY_RE = re.compile(r"sk-[A-Za-z0-9]{8,}")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def setup_logging(level: str = "INFO") -> None:
    """Root handler with a ``request_id`` default so third-party loggers
    (httpx, uvicorn, ...) that never set it cannot break formatting."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
            defaults={"request_id": "-"},
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def redact(text: str) -> str:
    text = _KEY_RE.sub("[redacted-key]", text)
    text = _EMAIL_RE.sub("[redacted-email]", text)
    return text[:500]


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True
