"""Deterministic input gate (OWASP LLM01 / LLM07 / LLM10).

Runs *before* the model call. Injection attempts get a canned refusal, not an
error code, so the endpoint does not become a probing oracle.
"""

import re
import unicodedata
from dataclasses import dataclass

# Direct instruction-override attempts.
_INJECTION_RES = (
    r"ignor(e|ing)\s+(previous|prior|all|above|your)\s+instructions?",
    r"disregard\s+.*instructions?",
    r"system\s+prompt|developer\s+prompt|reveal\s+.*instructions?",
    r"repeat\s+your\s+instructions?|print\s+your\s+instructions?",
    r"forget\s+.*instructions?|override\s+.*instructions?",
    r"\bdan\b|jailbreak|do\s+anything\s+now|developer\s+mode",
    r"base64|decode\(|os\.system|eval\(|exec\(",
    r"translate\s+.*instructions?|paraphrase\s+.*instructions?",
)

_INJECTION_RE = re.compile("|".join(f"(?:{p})" for p in _INJECTION_RES), re.IGNORECASE)

# Long base64-ish blobs often smuggle encoded instructions (LLM01 scenario #9).
# 40 chars keeps false positives rare in plain article requests while catching
# short smuggled payloads.
# Long base64-ish blobs often smuggle encoded instructions (LLM01 scenario #9).
# Padded blobs (>=20 chars + padding) or long unpadded runs. Thresholds keep
# false positives rare in plain article requests.
_BLOB_RE = re.compile(r"[A-Za-z0-9+/]{20,}={1,2}|[A-Za-z0-9+/]{60,}")

# Instruction-like phrasing smuggled mid-text.
_ROLE_SPOOF_RE = re.compile(
    r"\[(system|developer|assistant)\]|<\|\s*(system|user|assistant)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InputVerdict:
    allowed: bool
    reason: str = ""
    category: str = ""  # injection_probe | leak_probe | obfuscated | ok


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def screen_input(text: str) -> InputVerdict:
    """Classify raw user text. Pure function — no I/O, easy to test."""
    folded = normalize(text)
    if _INJECTION_RE.search(folded):
        return InputVerdict(False, "prompt-injection pattern detected", "injection_probe")
    if _ROLE_SPOOF_RE.search(folded):
        return InputVerdict(False, "role-spoof framing detected", "injection_probe")
    if "system prompt" in folded.lower() or "my instructions" in folded.lower():
        return InputVerdict(False, "system-prompt probe detected", "leak_probe")
    if _BLOB_RE.search(folded):
        return InputVerdict(False, "obfuscated payload detected", "obfuscated")
    return InputVerdict(True, "", "ok")
