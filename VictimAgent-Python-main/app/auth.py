"""API-key authentication.

Dev mode (``PROD_API_KEYS`` empty): open, matching the legacy contract.
Production: ``X-API-Key`` or ``Authorization: Bearer`` required, compared with
``hmac.compare_digest``. Failures return 401 without revealing which keys exist.
"""

import hmac
import logging

from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings

log = logging.getLogger(__name__)


def _provided_key(request: Request) -> str:
    header = request.headers.get("x-api-key", "")
    if header:
        return header.strip()
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


async def require_api_key(request: Request) -> None:
    settings = get_settings()
    allowed = settings.api_keys
    if not allowed:
        return None  # dev mode: auth not configured
    provided = _provided_key(request)
    if provided and any(hmac.compare_digest(provided, k) for k in allowed):
        return None
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")


# Re-export for FastAPI Depends without importing this module's privates.
RequireApiKey = Depends(require_api_key)
