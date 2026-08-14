---
description: Record a decision or insight into docs/ via the docs-keeper subagent
argument-hint: [what to record — a decision or an engine insight]
context: fork
agent: docs-keeper
---

Record the following into the project's `docs/`, choosing `docs/decisions.md`
(a choice with alternatives) or `docs/insights.md` (an engine gotcha / pattern)
as appropriate, and integrating it into the right section rather than appending
a duplicate:

$ARGUMENTS

If this involves an engine capability being built, extended, or retired — a new
stat, trigger, fill kind, reset trigger, spec-dict key, or primitive — also make
sure `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`
names it, and add it if not. A capability missing from that catalog reads to the
next session as one the engine does not have.

You start with a fresh context and cannot see the main conversation, so treat
the text above as the source of truth. If it's thin, reconstruct supporting
detail read-only from `git log` / `git show` / the code before writing. Report
what you recorded and where.
