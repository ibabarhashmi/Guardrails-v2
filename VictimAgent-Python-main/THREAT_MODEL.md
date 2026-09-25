# Threat model (one page)

## Assets
1. `OPENAI_API_KEY` — spend + quota abuse.
2. Model spend per request (DoW).
3. Response integrity — policy compliance is the product.
4. Operator reputation — Powers health-advice adjacent content.

## Actors
- Anonymous internet user (unauthenticated in dev; API-key in prod).
- RL adversary training jailbreak policies (uses `/victim` only).
- Curious user probing system instructions.

## Abuse cases → controls
1. **Jailbreak to tech/science** → role restriction, input gate, output topic
   enforcement, canned refusal (no oracle detail).
2. **System-prompt extraction** → leak probes refused; no prompt text in repo
   responses, errors, or logs.
3. **Denial of wallet** → auth, rate limits, body/input caps, `max_tokens`,
   timeout, single retry.
4. **PII exfiltration via output** → scrub + escape; logs redacted.
5. **Dependency compromise** → slim pins, audit, SBOM on release.

## Trust boundaries
- Client input: untrusted, validated at schema + gate.
- Model output: untrusted, validated at output gate.
- `src/agent.py` (victim): untrusted legacy; flag-gated, never default.

## Out of scope
Training/fine-tuning, tools/function-calling, RAG/vectors, MCP. Any of these
requires re-running this threat model.
