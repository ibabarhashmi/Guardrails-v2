"""Adversarial regression: every prompt in the suite must be refused somewhere.

Runs fully offline: input gate for direct probes, output gate for topic
violations (simulating a model that complied). `allow-gate-miss` documents
known blind spots (e.g. non-English injection) that the LLM instruction and
output gate must still catch at runtime.
"""

import json
import pathlib

from app.guards.input_gate import screen_input
from app.guards.output_gate import screen_output
from app.prompts import REFUSAL_MESSAGE

SUITE = pathlib.Path(__file__).parent.parent / "evals" / "jailbreak_suite.jsonl"


def load_suite():
    with open(SUITE) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def test_suite_refusals():
    failures = []
    for case in load_suite():
        prompt, expect = case["prompt"], case["expect"]
        if expect == "allow":
            if not screen_input(prompt).allowed:
                failures.append(f"over-refused benign: {prompt!r}")
        elif expect == "deny-input":
            if screen_input(prompt).allowed:
                failures.append(f"input gate missed: {prompt!r}")
        elif expect == "deny-output":
            assert screen_input(prompt).allowed, f"unexpected input deny: {prompt!r}"
            v = screen_output(prompt)  # model echoed/complied with the topic
            if v.message != REFUSAL_MESSAGE:
                failures.append(f"output gate missed: {prompt!r}")
        elif expect in ("allow-gate-miss", "deny-output-or-allow"):
            pass  # documented blind spots / ambiguous cases
        else:
            raise AssertionError(f"unknown expectation: {expect}")
    assert not failures, "\n".join(failures)


def test_suite_size_guarded():
    assert len(load_suite()) >= 15, "suite must not shrink silently"
