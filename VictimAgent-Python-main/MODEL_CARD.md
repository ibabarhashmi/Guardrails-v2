# Model card (service-level)

- **Purpose:** Short articles about Lifestyle, Health, or Fashion. All other
  topics refused with a canned message.
- **Model:** Configurable via `MODEL` (default `gpt-4o-mini`), Chat Completions.
- **Guardrails:** Deterministic input gate → model → deterministic output gate.
  The system prompt is advisory only, never the sole control.
- **Limitations:** Keyword-based topic enforcement over-refuses ambiguous
  tech-adjacent content by design. Health outputs carry a general-information
  disclaimer and are not medical advice.
- **Data:** Prompts/outputs are not persisted. Logs carry counts and verdicts
  only, with PII redacted. Set retention in your log pipeline (default: none).
- **Evaluation:** `evals/jailbreak_suite.jsonl` regression set must pass in CI;
  track jailbreak rate against `/victim` separately for research.
