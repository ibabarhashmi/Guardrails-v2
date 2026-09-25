"""Test setup: deterministic env, no network, no rate limiting."""

import os

os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["PROD_API_KEYS"] = "test-key-123"
os.environ["ENABLE_RATE_LIMIT"] = "false"
os.environ["ENABLE_VICTIM"] = "false"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

TEST_API_KEY = "test-key-123"


def auth_headers() -> dict:
    return {"X-API-Key": TEST_API_KEY}
