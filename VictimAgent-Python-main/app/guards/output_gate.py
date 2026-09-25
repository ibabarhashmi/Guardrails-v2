"""Deterministic output gate (OWASP LLM05 / LLM02 / LLM07 / LLM09).

Runs *after* the model call. The model is treated as an untrusted user:
off-topic output is replaced with a canned refusal, PII/secrets are scrubbed,
HTML is escaped, and prompt-echo is treated as leakage.
"""

import html
import re
from dataclasses import dataclass

from app.guards.policy import contains_allowed_topic, contains_denied_topic
from app.prompts import HEALTH_DISCLAIMER, REFUSAL_MESSAGE

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
_KEY_RE = re.compile(
    r"sk-[A-Za-z0-9]{8,}|api[_-]?key\s*[:=]\s*\S+|bearer\s+[A-Za-z0-9\-._~+/]+",
    re.IGNORECASE,
)

# If the model echoes its own instructions, that is leakage (LLM07).
_LEAK_RES = (
    r"ai article writer",
    r"instruction hierarchy",
    r"allowed topics \(only these\)",
)
_LEAK_RE = re.compile("|".join(_LEAK_RES), re.IGNORECASE)

REDACTED = "[redacted]"


def scrub_pii(text: str) -> str:
    text = _EMAIL_RE.sub(REDACTED, text)
    text = _PHONE_RE.sub(REDACTED, text)
    text = _KEY_RE.sub(REDACTED, text)
    return text


@dataclass(frozen=True)
class OutputVerdict:
    message: str
    decision: str = "allow"  # allow | deny
    reason: str = ""


def screen_output(text: str) -> OutputVerdict:
    """Enforce topic policy and scrub sensitive content. Pure function."""
    if not text or not text.strip():
        return OutputVerdict(REFUSAL_MESSAGE, "deny", "empty model output")

    if _LEAK_RE.search(text):
        return OutputVerdict(REFUSAL_MESSAGE, "deny", "prompt-echo leakage")

    if contains_denied_topic(text):
        return OutputVerdict(REFUSAL_MESSAGE, "deny", "off-topic model output")

    cleaned = scrub_pii(text.strip())
    cleaned = html.escape(cleaned, quote=True)

    if contains_allowed_topic(cleaned) and re.search(r"\bhealth\b", cleaned, re.IGNORECASE):
        if HEALTH_DISCLAIMER.lower() not in cleaned.lower():
            cleaned += f"\n{HEALTH_DISCLAIMER}"
    return OutputVerdict(cleaned, "allow", "")
