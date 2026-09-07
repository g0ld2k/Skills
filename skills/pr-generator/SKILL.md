---
name: pr-generator
description: Use when drafting, creating, or updating a GitHub pull request from current branch changes.
license: MIT
---

# PR Generator

Produce an evidence-based PR title and body; publish only when requested and
authorized. Drafting needs branch evidence, not publishing credentials.

## Evidence and Boundaries

- Establish repository, head branch, and base branch. Use a user/caller-provided
  base verbatim and report its source. Otherwise use existing branch context or
  `scripts/detect_base_branch.sh`; ask if the base cannot be determined.
- Inspect commits ahead of the base and the branch diff. Use local refs for
  offline drafting and state their freshness limitation. Do not invent a diff
  if the repository, base, commits, or changed files are missing.
- Read project terminology documents only when terminology is unresolved.
- Separate tests changed from tests actually run in this session. Report
  failures accurately; do not run tests merely to populate a PR template.
- Preserve unrelated work. Destructive Git operations need explicit authorization.
- Read [conventions](references/conventions.md) for authorization, external text,
  temporary files, capability fallback, and blocked-operation reporting.

## Choose the Requested Operation

For either operation, read [title heuristics](references/title-heuristics.md),
[style and body template](references/style-guide.md), and
[testing language](references/testing-language.md) when composing the draft.

### Draft

Return the title, body, base/head, tests changed, and tests run or not run.
Identify create vs update when known; label it unverified when remote lookup
is unavailable. Finish a draft-only request without requesting publication
approval or loading publishing instructions.

### Create or Update

Prepare and show the title, full body, base/head, and intended create/update
action before publication. The approval gate is explicit authorization from
the conversation or recorded caller scope covering this action and branch/base.
A new PR's branch push additionally needs push authorization. State the scope
and proceed when covered; ask only for missing authorization.

Read [publishing](references/publishing.md) for capability selection, fresh
remote checks, and commands. Read [failure handling](references/failure-handling.md)
only if an operation fails. Complete independent drafting or authorized diagnosis
while a publishing operation is blocked. This skill does not authorize merging.

## Output Contract

Provide the PR title/body, base/head, create vs update decision (or explicitly
unverified status), tests changed, and exact tests run/results or
`Not run in this session`. After publication, include the confirmed PR URL.
If publication is blocked, include the completed draft and specific blocker.
For this unnumbered workflow, replace the shared numbered Blocked Report with:

```text
BLOCKED: <operation> — <specific missing condition or failure>
Completed: <work actually completed>
Would unblock: <required capability, authorization, or correction>
```

Name the operation (for example, branch push, PR lookup, create, or update);
do not invent gate IDs or completed step numbers.

## Validation

When changing routing or authorization behavior, use the relevant scenarios in
[validation-scenarios](references/validation-scenarios.md).
