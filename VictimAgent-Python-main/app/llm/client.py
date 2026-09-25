"""OpenAI integration with bounded retries and safe error mapping.

- Async client, explicit timeout, capped output tokens (LLM10).
- Exactly one retry, only for retryable transient failures (429/5xx/timeout).
  No retry on 4xx or policy errors: the chat call is not idempotent-cheap and
  blind retries amplify spend.
- SDK internals never escape: callers get ``UpstreamError`` with a safe message.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.prompts import DEVELOPER_PROMPT

log = logging.getLogger(__name__)


class UpstreamError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


async def generate_response(user_texts: list[str], settings: Settings) -> str:
    from openai import (
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        AsyncOpenAI,
        RateLimitError,
    )

    client = AsyncOpenAI(
        api_key=settings.require_openai_key(),
        timeout=settings.LLM_TIMEOUT_S,
        max_retries=0,  # retries handled explicitly below
    )
    messages: list[dict[str, str]] = [{"role": "developer", "content": DEVELOPER_PROMPT}]
    messages += [{"role": "user", "content": t} for t in user_texts]

    last: Exception | None = None
    for attempt in (1, 2):
        try:
            completion = await client.chat.completions.create(
                model=settings.MODEL,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=settings.MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
            )
            content = (completion.choices[0].message.content or "").strip()
            if not content:
                raise UpstreamError("Empty model output", retryable=True)
            return content
        except UpstreamError:
            raise
        except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
            last = exc
            log.warning("llm transient failure attempt=%d err=%s", attempt, type(exc).__name__)
        except APIStatusError as exc:
            last = exc
            if exc.status_code is not None and 500 <= exc.status_code < 600:
                log.warning("llm 5xx attempt=%d status=%s", attempt, exc.status_code)
                continue
            raise UpstreamError("Upstream model request rejected", retryable=False) from exc
        if attempt == 1:
            await asyncio.sleep(0.5)
    raise UpstreamError("Upstream model temporarily unavailable", retryable=True) from last
