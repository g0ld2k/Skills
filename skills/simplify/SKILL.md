---
name: simplify
description: Use when a changed Git diff or explicitly supplied/thread-edited files need review for reuse, quality, or efficiency before commit readiness.
license: MIT
---

# Simplify: Code Review and Cleanup

Review one resolved scope for reuse, quality, and efficiency. Present only
evidence-backed findings, then fix only the selected items.

When a phase blocks, use the Blocked Report contract in
`references/conventions.md`. Identify `Phase 1` or `Phase 2` as the canonical
workflow-step owner and include the observed command, error, role, partition,
or oversized location in the one-line observation.

## Phase 1: Resolve Scope

Resolve exactly one review scope, in this order. Stop at the first branch that
applies.

1. **Changed diff.** Run both `git --no-pager diff` and
   `git --no-pager diff --staged`, and record each command's exit status,
   stderr, and patch output. A non-zero exit is a Git command failure: block
   with the command and error instead of treating it as an empty diff or using
   a fallback. If both commands succeed and either has patch output, review
   the union of their changed files and hunks only.
2. **Supplied or thread-edited files.** Only when both successful diff
   commands are empty, use explicit paths supplied by the caller or recorded
   as edited in this thread. Review those paths only. If a supplied path cannot
   be read, block and name it; do not broaden the scope.
3. **No scope.** When the successful diff is empty and no supplied or
   thread-edited paths exist, complete with `Reviewed scope: none` and
   `no actionable findings`. Do not launch reviewers or ask for finding IDs. If a
   caller explicitly requires a review target that is absent, block with the
   missing-scope observation instead.

For a diff, create a changed-file index containing each path, status,
added/deleted line counts, and hunk boundaries. For a fallback file set, use
these explicit fields: `path`, `source/status` (`supplied` or `thread-edited`),
`file boundary` (`whole file`), `line count`, `added: n/a`, and `deleted: n/a`.
This index is the scope record used by every reviewer and by the final report.

## Phase 2: Partition and Launch Reviewers

Keep every reviewer request within this exact, checkable context budget:
`MAX_REVIEW_REQUEST_BYTES = 48,000`. Render the complete request exactly as it
will be sent—including fixed instructions, the compact complete changed-file
index, and the assigned review content—encode it as UTF-8, and record its
actual byte count. Assigned review content means a diff partition for
changed-diff scope or line-numbered file content for fallback scope. Count
either kind in the rendered request, and require every request to be at or
below the cap.

Render and measure the fixed instructions plus the compact complete index
before partitioning. If that fixed portion alone exceeds
`MAX_REVIEW_REQUEST_BYTES`, fail closed and request a narrower scope. There is
no unbounded or truncated-artifact bypass for this cap.

Partition changed-diff content in this order: coherent whole files, hunks with
related hunks together, then coherent contiguous changed-line ranges for a
single oversized hunk. Use at most 20 unchanged context lines of overlap at
each changed-line boundary. Partition fallback content separately in this
order: whole files, then coherent bounded line-numbered ranges with at most 20
unchanged lines of overlap. Reduce each range or overlap until its rendered
request is at or below the cap.
Reviewers may inspect repository context read-only to understand an abstraction
or behavior. Every partition carries the complete changed-file index, its
partition identifier, and only its assigned review content; the parent must
not triplicate one oversized full diff in every prompt. If an indivisible
changed line or fallback-content unit still cannot fit after the fixed
instructions and index bytes, fail closed, identify its `path:line`, and
request a narrower scope.

Launch the three roles—reuse, quality, and efficiency—in parallel for each
partition when sub-agents are available; otherwise run the same role/partition
matrix sequentially. Wait for every dispatched request. If any reviewer call
fails, times out, is missing, or does not return a parseable JSON array, block
and identify the failed role and partition. Never aggregate a partial review
as complete.

Dispatch each agent with this prompt shape:

    You are the [reuse|quality|efficiency] reviewer for partition [id]. Scope
    findings to the assigned review content. For changed-diff scope this is a
    diff partition; for fallback scope it is line-numbered file content. The
    changed-file index below lists the complete reviewed scope. You may inspect repository context
    read-only to locate existing utilities or duplicates and cite their file
    paths. Do not edit files. Return ONLY a JSON array. Each finding must have
    keys: category ("[reuse|quality|efficiency]"), severity
    ("high"|"medium"|"low"), confidence ("high"|"medium"|"low"), location
    ("path:line" in the assigned scope), observed_evidence (one concise,
    concrete sentence naming what the code does at that location), summary
    (one sentence), proposed_fix (one sentence), existing_abstraction (the
    existing utility/abstraction name for reuse findings, otherwise null), and
    existing_abstraction_location (its repository path:line for reuse
    findings, otherwise null). Do not include an id; the parent assigns ids
    sequentially during aggregation. Severity and confidence definitions:
    [paste the Severity definitions and Confidence definitions blocks
    verbatim]. Review criteria: [paste that agent's numbered list].
    Changed-file index: [index]
    Assigned review content: [diff partition or line-numbered fallback content only]

1. Reuse pass
2. Quality pass
3. Efficiency pass

If sub-agents/parallel tools are available, run passes concurrently. Otherwise
run sequentially. The finding format must be identical either way.

### Agent 1: Code Reuse Review

For each change:

1. **Search for existing utilities and helpers** that could replace newly written code. Look for similar patterns elsewhere in the codebase—common locations are utility directories, shared modules, and files adjacent to the changed ones.
2. **Flag any new function that duplicates existing functionality.** Suggest the existing function to use instead.
3. **Flag any inline logic that could use an existing utility**—hand-rolled string manipulation, manual path handling, custom environment checks, ad-hoc type guards, and similar patterns are common candidates.

### Agent 2: Code Quality Review

Review the assigned changes for hacky patterns:

1. **Redundant state**: state that duplicates existing state, cached values that could be derived, observers/effects that could be direct calls
2. **Parameter sprawl**: adding new parameters to a function instead of generalizing or restructuring existing ones
3. **Copy-paste with slight variation**: near-duplicate code blocks that should be unified with a shared abstraction
4. **Leaky abstractions**: exposing internal details that should be encapsulated, or breaking existing abstraction boundaries
5. **Stringly-typed code**: using raw strings where constants, enums, or typed values already exist in the codebase
6. **Unnecessary nesting**: wrapper views/elements that add no layout value—check if inner component props already provide the needed behavior

### Agent 3: Efficiency Review

Review the assigned changes for efficiency:

1. **Unnecessary work**: redundant computations, repeated file reads, duplicate network/API calls, N+1 patterns
2. **Missed concurrency**: independent operations run sequentially when they could run in parallel
3. **Hot-path bloat**: new blocking work added to startup or per-request/per-render hot paths
4. **Unnecessary existence checks**: pre-checking file/resource existence before operating (TOCTOU anti-pattern)—operate directly and handle the error
5. **Memory**: unbounded data structures, missing cleanup, event listener or observer leaks
6. **Overly broad operations**: reading entire files when only a portion is needed, loading all items when filtering for one

### Required Findings Schema

Normalize every finding before presenting:

- `id`: integer, sequential from 1; assign only after evidence validation
- `category`: `reuse` | `quality` | `efficiency`
- `severity`: `high` | `medium` | `low`
- `confidence`: `high` | `medium` | `low`
- `location`: `path:line` in the resolved changed scope
- `observed_evidence`: one concise, concrete observation tied to the changed location
- `summary`: one sentence
- `proposed_fix`: one sentence
- `existing_abstraction`: existing utility or abstraction name for `reuse`, otherwise `null`
- `existing_abstraction_location`: repository `path:line` for `reuse`, otherwise `null`

Evidence is part of validity, not optional explanation. `location` must be in
the resolved changed scope, and `observed_evidence` must name a concrete
symbol, operation, or behavior visible there. A `reuse` finding is valid only
when it names the existing utility or abstraction and its repository
`path:line`; if the alternative was not located, report a different category
only when its evidence supports it, or omit the finding.

Before presentation, parse and normalize every reviewer result:

Reject or downgrade findings that do not meet the evidence requirements before
presentation: reject findings with no concrete evidence; downgrade confidence
to `low` when concrete evidence remains but cannot support a stronger
confidence.

1. Reject findings with missing required fields, invalid enum values,
   out-of-scope locations, vague or missing observed evidence, and `reuse`
   findings without both existing-abstraction fields. Never invent evidence.
2. When evidence is concrete but does not support the reported confidence,
   downgrade confidence to `low`; confidence is never upgraded during
   aggregation. Deduplicate overlapping findings and keep the clearest
   evidence-backed version.
3. Assign sequential integer IDs only after this gate. Findings rejected here
   are not presented or selectable; report their count and reason in the final
   validation note when non-zero.

If no valid findings remain after this gate, complete immediately with the
resolved reviewed scope and the exact result `no actionable findings`. Do not
present an empty list or ask for nonexistent IDs. A valid empty JSON array from
all successful reviewers is the normal zero-findings path.

Severity definitions:

- `high`: correctness-bug risk, security exposure, unbounded resource growth,
  or a measurable performance regression on a hot path introduced by this diff
- `medium`: duplication of an existing utility, leaky abstraction, or redundant
  work that compounds as the code grows—this is `medium` even when confidence
  is `high` (an exact, confidently-identified duplicate is still a duplication
  finding, not a correctness/security/growth finding, unless the duplicated
  code itself independently meets the `high` bar above)
- `low`: naming, style, or an optional refactor with no behavioral stakes

Confidence definitions:

- `high`: you located the existing utility, duplicate, or hot path and can name
  its file path
- `medium`: the pattern strongly suggests an issue but you did not verify the
  alternative exists
- `low`: heuristic match only

## Phase 3: Present Findings and Get User Selection

Wait for all three agents to complete. Aggregate their findings for
presentation. If a finding is a false positive or not worth addressing, note
it and move on—do not argue with the finding, just skip it. The evidence gate
above runs before any selection. Do not edit code in this phase.

If the caller passed a recorded unattended selection policy, use it as the
selection instead of asking again. The default unattended policy is: auto-select
only valid, in-scope medium/high findings with medium/high confidence. Findings
with low severity or low confidence stay unselected unless the recorded policy
explicitly includes them. Report the policy and selected finding IDs before
applying fixes.

Low-confidence handling is the same rule in both modes:

| Mode | Medium/high findings | Low-confidence findings |
| --- | --- | --- |
| Attended | Show; apply only when selected | Show; apply only when the user explicitly selects the ID (`all` counts as explicit) |
| Unattended | Auto-select only when valid, in scope, and medium/high confidence | Low severity or low confidence stays unselected by default; select only when the recorded policy explicitly includes it |

An invalid or rejected finding never becomes selectable through either mode.

1. Present findings as a numbered list with this display format:
   - `[id] [severity] [category] [confidence] path:line - summary`
   - `Evidence: observed_evidence`
   - For reuse: `Existing abstraction: name (path:line)`
   - `Fix: proposed_fix`
2. Ask the user:
   - `Select items to address (e.g. 1,2,5,8), or reply all/none.`
3. Parse selection:
   - `all` -> select all findings
   - `none` -> select none
   - `1,2,5` -> select valid IDs only
4. If invalid IDs are included, ignore them, proceed with the valid IDs, and
   name the ignored IDs in the response. If no valid IDs remain, ask once for
   clarification. This rule applies only when findings were presented; the
   zero-findings path never asks for IDs.

## Phase 4: Apply Selected Fixes

Apply only selected findings.

Rules:

1. Keep edits minimal and behavior-preserving unless the user explicitly approves behavior changes.
2. Skip low-confidence findings unless explicitly selected by the attended user or included by the recorded unattended policy.
3. If a selected finding is a false positive or not worth changing, skip it and record a one-line reason.
4. Prefer existing abstractions/utilities over adding new ones.
5. Run targeted validation for touched areas when possible (tests/lint/typecheck scoped to changed files).

Final response must include:

1. Reviewed scope and scope-source decision (changed diff, supplied/thread-edited fallback, or none)
2. Applied findings (by ID)
3. Skipped selected findings (with reason)
4. Unselected findings
5. Rejected findings and evidence-gate reasons, when any
6. Validation run (or why validation was not run)
7. Whether selection came from user choice or a recorded unattended policy
8. For zero findings, the exact result `no actionable findings` and no ID request

## References

- `references/conventions.md` for the required Blocked Report format.
- `references/validation-scenarios.md` for RED/GREEN checks when changing this
  skill.
