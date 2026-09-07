---
name: simplify
description: Use when reviewing changed code for reuse, quality, or efficiency issues after code changes and before commit readiness.
license: MIT
---

# Simplify: Code Review and Cleanup

Review changed files for reuse, quality, and efficiency. Present findings to the user, then fix only the selected items.


## Phase 1: Identify Changes

Find the exact scope to review.

1. Check unstaged and staged changes.
2. Prefer reviewing only changed files.
3. If no git diff exists, review files the user referenced or files edited in this thread.

```bash
# unstaged
git --no-pager diff

# staged
git --no-pager diff --staged
```

If both are empty, stop and report there is no diff to simplify.

## Phase 2: Review Reuse, Quality, and Efficiency

Cover all three concerns below. Review small or tightly coupled diffs locally.
Delegate independent portions when their size or complexity makes separate
review useful and the host supports it; no fixed agent count is required.

Give each delegated reviewer a bounded read-only scope, the relevant diff and
sufficient surrounding context, and the finding fields and definitions below.
Reviewers may search for existing utilities and cite their locations. The
parent combines findings and assigns sequential ids. Use the same finding
schema whether reviewing locally or delegating.

### Code Reuse Review

For each change:

1. **Search for existing utilities and helpers** that could replace newly written code. Look for similar patterns elsewhere in the codebase — common locations are utility directories, shared modules, and files adjacent to the changed ones.
2. **Flag any new function that duplicates existing functionality.** Suggest the existing function to use instead.
3. **Flag any inline logic that could use an existing utility** — hand-rolled string manipulation, manual path handling, custom environment checks, ad-hoc type guards, and similar patterns are common candidates.

### Code Quality Review

Review the same changes for hacky patterns:

1. **Redundant state**: state that duplicates existing state, cached values that could be derived, observers/effects that could be direct calls
2. **Parameter sprawl**: adding new parameters to a function instead of generalizing or restructuring existing ones
3. **Copy-paste with slight variation**: near-duplicate code blocks that should be unified with a shared abstraction
4. **Leaky abstractions**: exposing internal details that should be encapsulated, or breaking existing abstraction boundaries
5. **Stringly-typed code**: using raw strings where constants, enums, or typed values already exist in the codebase
6. **Unnecessary nesting**: wrapper views/elements that add no layout value — check if inner component props already provide the needed behavior

### Efficiency Review

Review the same changes for efficiency:

1. **Unnecessary work**: redundant computations, repeated file reads, duplicate network/API calls, N+1 patterns
2. **Missed concurrency**: independent operations run sequentially when they could run in parallel
3. **Hot-path bloat**: new blocking work added to startup or per-request/per-render hot paths
4. **Unnecessary existence checks**: pre-checking file/resource existence before operating (TOCTOU anti-pattern) — operate directly and handle the error
5. **Memory**: unbounded data structures, missing cleanup, event listener or observer leaks
6. **Overly broad operations**: reading entire files when only a portion is needed, loading all items when filtering for one

### Required Findings Schema

Normalize every finding before presenting:

- `id`: integer, sequential from 1
- `category`: `reuse` | `quality` | `efficiency`
- `severity`: `high` | `medium` | `low`
- `confidence`: `high` | `medium` | `low`
- `location`: `path:line`
- `summary`: one sentence
- `proposed_fix`: one sentence

Deduplicate overlapping findings and keep the clearest one.

Severity definitions:

- `high`: correctness-bug risk, security exposure, unbounded resource growth,
  or a measurable performance regression on a hot path introduced by this diff
- `medium`: duplication of an existing utility, leaky abstraction, or redundant
  work that compounds as the code grows — this is `medium` even when
  confidence is `high` (an exact, confidently-identified duplicate is still a
  duplication finding, not a correctness/security/growth finding, unless the
  duplicated code itself independently meets the `high` bar above)
- `low`: naming, style, or an optional refactor with no behavioral stakes

Confidence definitions:

- `high`: you located the existing utility, duplicate, or hot path and can name
  its file path
- `medium`: the pattern strongly suggests an issue but you did not verify the
  alternative exists
- `low`: heuristic match only

## Phase 3: Present Findings and Get User Selection

Complete all relevant review work, including any delegated reviews, and aggregate the findings. Skip false positives or findings not worth addressing and record the reason.

Do not edit code in this phase.

If the user or caller supplied a recorded unattended selection policy, use it as the
selection instead of asking again. The default unattended policy is: select
valid, in-scope medium/high findings; leave low findings unselected unless the
policy explicitly includes them. Report the policy and selected finding ids
before applying fixes.

1. Present findings as a numbered list with this display format:
   - `[id] [severity] [category] [confidence] path:line - summary`
   - `Fix: proposed_fix`
2. If no applicable selection or unattended policy is already recorded, ask the user:
   - `Select items to address (e.g. 1,2,5,8), or reply all/none.`
3. Parse selection:
   - `all` -> select all findings
   - `none` -> select none
   - `1,2,5` -> select valid ids only
4. If invalid ids are included, ignore them, proceed with the valid ids, and name the ignored ids in the response. If no valid ids remain, ask once for clarification.

## Phase 4: Apply Selected Fixes

Apply only selected findings.

Rules:

1. Keep edits minimal and behavior-preserving unless user explicitly approves behavior changes.
2. Skip low-confidence findings unless explicitly selected.
3. If a selected finding is a false positive or not worth changing, skip it and record a one-line reason.
4. Prefer existing abstractions/utilities over adding new ones.
5. Run targeted validation for touched areas when possible (tests/lint/typecheck scoped to changed files).

Final response must include:

1. Applied findings (by id)
2. Skipped selected findings (with reason)
3. Unselected findings
4. Validation run (or why validation was not run)
5. Whether selection came from user choice or a recorded unattended policy
