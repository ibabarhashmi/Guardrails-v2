# Security policy

## Scope

VictimAgent v2 (`POST /api/v1/chat`) is a policy-bound article API (Lifestyle /
Health / Fashion only). The legacy oracle (`POST /api/v1/victim/chat`) is
intentionally vulnerable and must only run locally with `ENABLE_VICTIM=true`
for red-team research. Never expose it publicly.

## Controls (mapped to OWASP LLM Top 10:2025)

| Risk | Control |
|---|---|
| LLM01 Prompt injection | Client roles restricted to `user`; server-side message construction; deterministic input gate; instruction-hierarchy developer prompt |
| LLM02 Sensitive disclosure | Secrets via env only, fail-closed boot; PII scrub on outputs; redacted logs; sanitized 4xx/5xx |
| LLM03 Supply chain | Pinned slim deps, `pip-audit` + Dependabot in CI, non-root distroless-style image |
| LLM05 Output handling | Zero-trust output gate: topic enforcement, prompt-echo detection, HTML escaping |
| LLM07 Prompt leakage | No secrets in prompts; leak probes refused without oracle feedback |
| LLM09 Misinformation | Topic confinement + health disclaimer; no authoritative claims outside scope |
| LLM10 Consumption | Input/body caps, `max_tokens`, timeouts, per-IP rate limits, single retry |

LLM04/LLM06/LLM08 are not applicable: no training data, no tools/RAG/vectors.
Adding tools, RAG, or MCP re-opens those risks and requires a new review
(least-privilege scopes, human approval, content segregation).

## Reporting

Do not include API keys or full prompts in reports. Redact as `[redacted]`.
