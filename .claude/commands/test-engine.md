---
description: Run the backend test suite (and optionally add interaction/regression tests) via the engine-test-runner subagent
argument-hint: [optional — a newly-encoded character to add interaction tests for]
context: fork
agent: engine-test-runner
---

Run the deck-builder's full backend test suite and report the exact pass/fail
summary line.

Focus (may be empty): $ARGUMENTS

If a focus is given above — e.g. a newly-encoded character — also add targeted
interaction / regression tests for it per your guidelines (shared-stat
stacking, whether a newly-relied-on stat is actually consumed, burst rotation
with the added unit), then rerun the suite. If no focus is given, just run the
suite and report; do not add tests.
