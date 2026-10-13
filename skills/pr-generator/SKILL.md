---
name: pr-generator
description: Draft, create, or update a GitHub pull request title and body from branch changes.
license: MIT
---

# PR authoring

Produce a concise, evidence-based title and body for the requested branch and
base. Preserve a supplied base; otherwise use existing branch context or
`scripts/detect_base_branch.sh`, asking only if the target remains ambiguous.
Inspect commits and the diff against that base. Offline drafting is useful:
label stale or missing remote evidence instead of requiring publishing access.

Use [writing conventions](references/style-guide.md) when composing the draft,
and [shared conventions](references/conventions.md) for authority and evidence.
Honor the user's format or repository template. Do not run tests just to fill
in a PR template, and distinguish tests changed from results actually observed.

For a draft-only request, return the title/body and relevant base/head or evidence
gaps. Do not ask to publish or load publication instructions.

For a requested create/update, prepare the concrete title, body, head and base.
Read [publishing](references/publishing.md) before writing. Reuse existing
permission for the operation and targets; a new branch push needs its own
applicable scope. Ask only for missing authority, not another confirmation of
covered work. PR creation or editing never authorizes merging.

After publication, confirm the PR URL, head/base and resulting title/body. If
blocked, deliver the draft with the specific remaining operation and condition.
Read [failure handling](references/failure-handling.md) only when needed.

Use the affected [validation scenarios](references/validation-scenarios.md) when
changing routing or authorization behavior.
