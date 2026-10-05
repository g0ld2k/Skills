---
name: pr-closeout-loop
description: Check an existing PR's readiness, or carry out explicitly requested bounded closeout work.
license: MIT
disable-model-invocation: true
---

# PR readiness and closeout

Use this explicitly selected workflow for one existing PR. Default to one
readiness pass. Do not choose branch topology, create integration branches,
start background monitoring, or merge as an implied next step.

Resolve repository/PR, head repository/ref/SHA, base branch/SHA, requested work,
and existing authority. Read [shared conventions](references/conventions.md).
Fetch current checks, mergeability, unresolved threads with replies, latest
reviews and actionable conversation feedback. Report gaps instead of treating
missing evidence as success.

If fixes are requested, use `pr-comment-review` for feedback handling and an
appropriate debugging workflow for failed checks. Preserve unrelated work and
verify an editing checkout matches the intended PR head. Use focused review
when warranted; `simplify` and `commit-message` are optional aids, not compulsory
transitions. Reuse existing authorization and relevant successful verification.
Commit/push only within scope; verify the resulting remote PR head.

Return readiness, completed work, current head/base, validation and CI evidence,
and the specific remaining blockers. A readiness report does not authorize a
write or imply a merged PR.

## Monitoring or merge requested

Read [monitoring and merge](references/monitoring-and-merge.md) only for those
operations. Existing requested unattended scope can cover repeated valid work;
record its target, allowed actions and stopping condition rather than repeatedly
asking for the same approval. Stop when the work is complete, the budget expires,
or a human decision is needed. Do not create a scheduled task without a request.

Use [validation scenarios](references/validation-scenarios.md) when changing
readiness, freshness, authority, or stopping behavior.
