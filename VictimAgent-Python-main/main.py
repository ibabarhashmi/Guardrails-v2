"""VictimAgent v2 — hardened FastAPI entrypoint.

Routes:
  GET  /healthz, /readyz            unauthenticated probes
  POST /api/v1/chat                 hardened production path (default)
  POST /api/v1/victim/chat          legacy vulnerable oracle; only when
                                    ENABLE_VICTIM=true (RL research). Disabled
                                    by default.

Response shape stays backward compatible: ``{"message": str}`` plus additive
``request_id`` and ``policy`` fields.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth import RequireApiKey
from app.config import get_settings
from app.guards.input_gate import screen_input
from app.guards.output_gate import screen_output
from app.llm.client import UpstreamError, generate_response
from app.observability import RequestIdFilter, new_request_id, redact, setup_logging
from app.prompts import REFUSAL_MESSAGE
from app.schemas import ChatRequest, ChatResponse, PolicyInfo

log = logging.getLogger("victimagent")


class _RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or new_request_id()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


class _HardeningMiddleware(BaseHTTPMiddleware):
    """Body-size cap + security headers. No body is echoed anywhere."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        try:
            length = int(request.headers.get("content-length", "0") or "0")
        except ValueError:
            length = 0
        if length > settings.MAX_BODY_BYTES:
            return JSONResponse(
                {"detail": "Request body too large", "request_id": self._rid(request)},
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @staticmethod
    def _rid(request: Request) -> str:
        return getattr(request.state, "request_id", "-")


def _sanitized_validation_errors(exc: RequestValidationError) -> list[dict]:
    """Strip raw input values so 422s cannot echo prompts back."""
    clean: list[dict] = []
    for err in exc.errors():
        clean.append({"loc": list(err.get("loc", [])), "msg": err.get("msg", "")})
    return clean


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logging.getLogger().addFilter(RequestIdFilter())
    try:
        settings.require_openai_key()
    except RuntimeError:
        log.error("boot refused: OPENAI_API_KEY missing", extra={"request_id": "-"})
        raise
    if settings.ENABLE_VICTIM:
        log.warning(
            "victim oracle ENABLED at /api/v1/victim/chat (research only)",
            extra={"request_id": "-"},
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="VictimAgent v2", version="2.0.0", lifespan=lifespan)

    app.add_middleware(_RequestIdMiddleware)
    app.add_middleware(_HardeningMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allow_hosts)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-API-Key", "Authorization"],
            max_age=600,
        )

    limiter = None
    if settings.ENABLE_RATE_LIMIT:
        from slowapi import Limiter
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
        from slowapi.util import get_remote_address

        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)

        async def _rate_handler(request: Request, exc: RateLimitExceeded):
            return JSONResponse(
                {"detail": "Rate limit exceeded", "request_id": _rid(request)},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        app.add_exception_handler(RateLimitExceeded, _rate_handler)  # type: ignore[arg-type]

    def _rid(request: Request) -> str:
        return getattr(request.state, "request_id", "-")

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            {
                "detail": "Invalid request",
                "errors": _sanitized_validation_errors(exc),
                "request_id": _rid(request),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(FastAPIHTTPException)
    async def _http_handler(request: Request, exc: FastAPIHTTPException):
        return JSONResponse(
            {"detail": exc.detail, "request_id": _rid(request)},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        log.exception("unhandled error", extra={"request_id": _rid(request)})
        return JSONResponse(
            {"detail": "Internal server error", "request_id": _rid(request)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz():
        try:
            get_settings().require_openai_key()
        except RuntimeError:
            return JSONResponse({"status": "not-ready"}, status_code=503)
        return {"status": "ready"}

    async def _hardened_chat(body: ChatRequest, request: Request) -> ChatResponse:
        rid = _rid(request)
        started = time.perf_counter()
        user_texts = [m.content for m in body.messages]
        combined = "\n".join(user_texts)

        verdict = screen_input(combined)
        if not verdict.allowed:
            log.warning(
                "input gate deny category=%s reason=%s",
                verdict.category,
                verdict.reason,
                extra={"request_id": rid},
            )
            return ChatResponse(
                message=REFUSAL_MESSAGE,
                request_id=rid,
                policy=PolicyInfo(decision="deny", reason=verdict.reason, gate="input"),
            )

        try:
            raw = await generate_response(user_texts, get_settings())
        except UpstreamError as exc:
            code = 503 if exc.retryable else 502
            raise FastAPIHTTPException(code, "Upstream model temporarily unavailable")

        out = screen_output(raw)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "chat decision=%s reason=%s latency_ms=%d in_chars=%d out_chars=%d",
            out.decision,
            redact(out.reason),
            elapsed_ms,
            len(combined),
            len(out.message),
            extra={"request_id": rid},
        )
        return ChatResponse(
            message=out.message,
            request_id=rid,
            policy=PolicyInfo(
                decision="deny" if out.decision == "deny" else "allow",
                reason=out.reason,
                gate="output" if out.decision == "deny" else "none",
            ),
        )

    if limiter is not None:
        _hardened_chat = limiter.limit(get_settings().RATE_LIMIT)(_hardened_chat)  # type: ignore[assignment]

    app.post("/api/v1/chat", response_model=ChatResponse, dependencies=[RequireApiKey])(
        _hardened_chat
    )

    # --- Legacy vulnerable oracle (research only) ---
    if settings.ENABLE_VICTIM:

        @app.post("/api/v1/victim/chat", dependencies=[RequireApiKey])
        async def victim_chat(body: ChatRequest, request: Request):
            from src.agent import createResponse  # lazy: keeps import side-effect-free

            rid = _rid(request)
            log.warning("victim oracle invoked", extra={"request_id": rid})
            legacy = [{"role": "user", "content": m.content} for m in body.messages]
            try:
                import asyncio

                text = await asyncio.to_thread(createResponse, legacy)
            except Exception as exc:
                log.exception("victim oracle failure", extra={"request_id": rid})
                raise FastAPIHTTPException(502, "Victim oracle failed") from exc
            return {"message": text, "request_id": rid, "policy": {"decision": "allow"}}

    return app


app = create_app()
