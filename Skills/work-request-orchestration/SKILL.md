---
name: work-request-orchestration
description: Use when turning GitHub issues, milestones or epics, a single issue, a general work request, or an external plan into a disciplined implementation, validation, PR, review, and merge workflow.
tools:
  - bash
  - view
  - edit
  - grep
  - glob
  - Agent
---

# Work Request Orchestration

## Core Principle

Treat the request as an input queue, not as source truth. Verify the current
repo, issue, PR, branch, and instruction state; slice the work into reviewable
units; then run each unit through implementation, validation, simplify,
commit, PR, review/CI, and merge.

## Use For

- A set of GitHub issues, a milestone, or an epic.
- One GitHub issue or bug report.
- A general request that needs code changes.
- A plan from another session, tool, or LLM.
- A follow-up request such as "continue" when previous work is unfinished.

## Required Sub-Skills

- **REQUIRED:** Use `superpowers:using-git-worktrees` before implementation work
  when the current workspace is not already isolated.
- **REQUIRED:** Use `superpowers:brainstorming` before creating or changing
  product behavior, or when requirements are ambiguous.
- **REQUIRED:** Use `superpowers:writing-plans` for multi-step implementation
  work before touching code.
- **REQUIRED:** Use `superpowers:test-driven-development` for bug fixes,
  features, refactors, and behavior changes unless the user explicitly exempts
  the task.
- **REQUIRED BEFORE COMMIT:** Use `simplify` for non-trivial code changes.
- **REQUIRED FOR COMMITS:** Use `commit-message`.
- **REQUIRED FOR PRS:** Use `pr-generator`.
- **REQUIRED AFTER PR OPEN:** Use `codex-pr-approval-loop` when the user asks to
  monitor/address/merge or grants merge authority for the run.

## Workflow

### Phase 0: Preflight

1. Read repo instructions (`AGENTS.md`, `CLAUDE.md`, project docs) and current
   user approvals.
2. Check `git status --short --branch`, remotes, current branch/worktree, and
   default branch.
3. Fetch live source truth for referenced issues, PRs, comments, checks, and
   milestones. Treat handoff plans as context until verified.
4. Record unrelated dirty/untracked files and do not stage or rewrite them.
5. Ask only for blocking ambiguity. If the user gave blanket approval to commit,
   push, create PRs, and merge for this run, do not re-prompt at each routine
   publish step.

### Phase 1: Slice The Work

Choose the smallest independently reviewable unit:

| Input | Default slice |
| --- | --- |
| Multiple issues | One branch, commit, and PR per issue |
| Milestone or epic | One PR per issue or coherent dependency slice |
| Single issue | One branch, commit, and PR |
| General request | One PR unless it naturally splits by behavior |
| External plan | Re-derive slices from current source truth |

Stack PRs only when a later unit cannot be tested or reviewed without an
earlier unit. Otherwise branch each unit from the updated default branch after
the previous PR merges.

### Phase 2: Plan Each Unit

For each unit, write a short execution note before editing:

- source truth and acceptance criteria;
- files likely to change;
- failing or targeted tests to write first;
- local verification commands;
- PR/merge dependencies;
- human-gated decisions that must not be made silently.

Use `docs/superpowers/plans/` for repo plans unless project instructions say
otherwise. Keep plans out of focused issue PRs unless the plan itself is part of
the requested deliverable.

### Phase 3: Implement

For each unit:

1. Start from the correct base branch or isolated worktree.
2. Write or adjust the failing test first when behavior changes.
3. Make the smallest scoped implementation.
4. Run targeted tests, then the repo baseline when package, shared, CI, or
   broad behavior changes are involved.
5. Preserve unrelated local work and generated artifacts outside the unit.

For mechanical-only work, define a measurable guard first: test inventory,
`rg` assertion, lint failure, file count, or equivalent.

### Phase 4: Simplify And Commit

1. Review `git diff` and `git diff --staged`.
2. Run `simplify` for non-trivial code changes.
3. Address valid in-scope medium/high findings; use judgment on lows.
4. Re-run affected validation after simplify edits.
5. Stage only intended files.
6. Use `commit-message`; if blanket approval is active, commit after verifying
   the message is grounded in the staged diff.

### Phase 5: PR, Review, CI, Merge

1. Use `pr-generator` for PR title/body. Include exact tests actually run.
2. Push and create/update the PR when approval covers the publish step.
3. Run `codex-pr-approval-loop` for review comments, CI failures, fresh Codex
   approval, and merge readiness.
4. Treat approval as fresh only for the current head SHA and current PR body.
5. Merge only when required checks are green, actionable feedback is handled,
   approval is fresh, branch protection allows it, and no human-gated decision
   remains.
6. After merge, fetch the default branch before starting the next unit.

## Guardrails

- Do not invent issue details, test results, approvals, or remote state.
- Do not bundle unrelated fixes because they are nearby.
- Do not merge on old approval after pushing new commits or materially editing
  the PR body.
- Do not silently perform repo-admin, release, credential, billing, or policy
  decisions; document or ask.
- Do not let a reusable-skill request default to an install-only location when
  the user asked for a source-controlled skills project.
- Stop and report if tool limits, auth, permissions, unavailable logs, or
  conflicting feedback make progress unsafe.

## Red Flags

Stop and re-check the workflow when you think:

- "The plan already says what to do, so I do not need current source truth."
- "These issues are close enough to combine."
- "The tests can come after the fix."
- "This unrelated dirty file is probably mine."
- "The old approval still counts after this push."
- "The user said merge, so CI/review freshness does not matter."

## Output Contract

For planning output, include:

1. source truth checked;
2. work slices and order;
3. per-slice validation gates;
4. commit/PR/merge policy.

For execution output, include:

1. branches, commits, PR URLs, and merge SHAs;
2. validation run with exact command outcomes;
3. simplify findings addressed or deferred;
4. unresolved blockers or follow-ups.

## Validation Reference

When creating or editing this skill, read
`references/validation-scenarios.md` and run the scenarios before deploying.
