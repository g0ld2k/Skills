---
name: simplify
description: "Review changed code for reuse, quality, and efficiency, then fix selected issues. Use after code changes to catch duplication, hacky patterns, and inefficiencies before committing."
tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Edit
  - Agent
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

## Phase 2: Launch Three Review Agents in Parallel

Use the Agent tool to launch all three agents concurrently in a single message. Pass each agent the full diff so it has complete context.

1. Reuse pass
2. Quality pass
3. Efficiency pass

If sub-agents/parallel tools are available, run passes concurrently. Otherwise run sequentially. The finding format must be identical either way.

### Agent 1: Code Reuse Review

For each change:

1. **Search for existing utilities and helpers** that could replace newly written code. Look for similar patterns elsewhere in the codebase — common locations are utility directories, shared modules, and files adjacent to the changed ones.
2. **Flag any new function that duplicates existing functionality.** Suggest the existing function to use instead.
3. **Flag any inline logic that could use an existing utility** — hand-rolled string manipulation, manual path handling, custom environment checks, ad-hoc type guards, and similar patterns are common candidates.

### Agent 2: Code Quality Review

Review the same changes for hacky patterns:

1. **Redundant state**: state that duplicates existing state, cached values that could be derived, observers/effects that could be direct calls
2. **Parameter sprawl**: adding new parameters to a function instead of generalizing or restructuring existing ones
3. **Copy-paste with slight variation**: near-duplicate code blocks that should be unified with a shared abstraction
4. **Leaky abstractions**: exposing internal details that should be encapsulated, or breaking existing abstraction boundaries
5. **Stringly-typed code**: using raw strings where constants, enums, or typed values already exist in the codebase
6. **Unnecessary nesting**: wrapper views/elements that add no layout value — check if inner component props already provide the needed behavior

### Agent 3: Efficiency Review

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

## Phase 3: Present Findings and Get User Selection

Wait for all three agents to complete. Aggregate their findings for presentation. If a finding is a false positive or not worth addressing, note it and move on — do not argue with the finding, just skip it.

Do not edit code in this phase.

1. Present findings as a numbered list with this display format:
   - `[id] [severity] [category] path:line - summary`
   - `Fix: proposed_fix`
2. Ask the user:
   - `Select items to address (e.g. 1,2,5,8), or reply all/none.`
3. Parse selection:
   - `all` -> select all findings
   - `none` -> select none
   - `1,2,5` -> select valid ids only
4. If invalid ids are included, ignore invalid ids and proceed with valid ids. If no valid ids remain, ask once for clarification.

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
