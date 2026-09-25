"""Topic policy: what the agent may write about.

Deterministic keyword enforcement backing the LLM instruction (OWASP LLM01/05).
Over-refusal on ambiguous tech-adjacent lifestyle content is accepted and
documented: this agent is policy-bound by design.
"""

import re

# Terms that indicate a disallowed (tech/science) topic.
_DENIED_PATTERNS = (
    r"semiconductor|microchip|transistor|lithography",
    r"\bpython\b|\bjava\b|\bjavascript\b|\bgolang\b|\brust\b|\bsql\b",
    r"kubernetes|docker|terraform|aws|azure|linux|kernel",
    r"cybersecurity|malware|exploit|ransomware|phishing|hacker",
    r"quantum|neural network|machine learning|large language model|\bllm\b",
    r"fine-tun|retrieval augmented|transformer model|diffusion model",
    r"\bphysics\b|\bchemistry\b|\bbiology\b|astronomy|astrophysics",
    r"blockchain|crypto|bitcoin|stock market",
)

_DENIED_RE = re.compile("|".join(f"(?:{p})" for p in _DENIED_PATTERNS), re.IGNORECASE)

# Terms signalling an allowed topic (used for logging context only).
_ALLOWED_RE = re.compile(
    r"lifestyle|wellness|mindful|fitness|nutrition|diet|fashion|style|outfit|"
    r"skincare|health|sleep|exercise|meditation|yoga|travel|home|decor|beauty",
    re.IGNORECASE,
)


def contains_denied_topic(text: str) -> bool:
    return bool(_DENIED_RE.search(text))


def contains_allowed_topic(text: str) -> bool:
    return bool(_ALLOWED_RE.search(text))
