---
name: work-request-orchestration
description: Use when driving a work request (issues, milestone, epic, or external plan) through implementation, validation, PR, and merge.
license: MIT
compatibility: >-
  Requires a client/session authoritative skill catalog; applicable external
  prerequisites are superpowers:using-git-worktrees, superpowers:brainstorming,
  superpowers:writing-plans, superpowers:test-driven-development, and
  superpowers:systematic-debugging.
---

# Work Request Orchestration

## Prerequisite Gate

Run this gate as step 0, before any task-related repository, filesystem, Git,
network, or other external-state read or mutation. The client/session's
authoritative skill catalog is the only availability source; do not infer
availability from files, manifests, prior turns, or a partial invocation.

Read the complete client/session catalog with exact qualified names once and
cache that snapshot for the run. For each work unit, record `catalog_source`,
`required`, `present`, and `missing` before continuing. This plugin's bundled
catalog identities are
`g0ld2k-skills:simplify`, `g0ld2k-skills:commit-message`,
`g0ld2k-skills:pr-generator`, `g0ld2k-skills:pr-comment-review`,
and `g0ld2k-skills:pr-closeout-loop`; use the catalog spelling verbatim.

Use this branch matrix; a dash means an empty dependency set, not permission
to probe for a dependency:

| Active branch | Required qualified catalog names |
| --- | --- |
| Source-truth triage or disposition only | — |
| Implementation in a non-isolated workspace | `superpowers:using-git-worktrees` |
| Ambiguous or behavior-changing implementation | `superpowers:brainstorming` |
| Multi-step implementation | `superpowers:writing-plans` |
| Bug fix, feature, refactor, or behavior change without an explicit TDD exemption | `superpowers:test-driven-development` |
| Failing-check diagnosis | `superpowers:systematic-debugging` |
| Non-trivial change before commit | `g0ld2k-skills:simplify` |
| Commit | `g0ld2k-skills:commit-message` |
| PR creation or update | `g0ld2k-skills:pr-generator` |
| Direct review replies | `g0ld2k-skills:pr-comment-review` |
| PR closeout | `g0ld2k-skills:pr-closeout-loop`, `g0ld2k-skills:pr-comment-review` |

At step 0, gate the source-truth triage/disposition row only. A request or
authorization to implement does not activate implementation dependencies until
live evidence marks a unit `actionable`. For each actionable unit, select its
intended lifecycle and take the union of every foreseeable row, including
implementation, commit, PR, closeout, and transitive orchestration handoffs,
before the lifecycle's first side effect. Reuse the cached catalog snapshot and
derived closure; do not rescan it for each unit or helper. If later evidence
activates a conditional row that was not knowable then, extend the closure
against the snapshot before its first side effect. Refresh only if the client
reports that the catalog changed. Never require an inactive row, stop at the
first missing name, or substitute a similarly named skill. Report
every missing name in the active closure together. A missing bundled name
means the `g0ld2k-skills` installation is broken or incomplete: stop and give
reinstall/upgrade guidance, then require a fresh catalog. A missing
`superpowers:*` name is an install prerequisite: name it exactly and require
installation before that branch. If the catalog cannot be exposed, emit:

    BLOCKED: P0 — authoritative skill catalog unavailable; prerequisites cannot be verified
    Last completed step: 0
    Would unblock: expose the complete client/session catalog with exact qualified names and provider/source

Do not read the repository or probe dependencies after this block. For missing
entries, emit one report containing the full `missing` list and the same
three-line Blocked Report shape; do not invoke any dependency to discover
whether it is present.

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
- **REQUIRED BEFORE COMMIT:** Use `g0ld2k-skills:simplify` for non-trivial code
  changes (non-trivial per `g0ld2k-skills:pr-closeout-loop`'s definition: logic, behavior, tests, CI,
  package, workflow, public-contract, or meaningful docs/process changes).
  Pass: the recorded unattended selection policy when blanket approval is
  active (default: auto-address valid in-scope medium/high findings without
  re-prompting). Expect back: numbered findings applied per that policy, or
  presented for user selection in attended runs.
- **REQUIRED FOR COMMITS:** Use `g0ld2k-skills:commit-message`.
  Pass: staged diff, an explicit `message+commit` mode request, plus the
  recorded approval scope (blanket commit approval means commit with the
  generated message once it is grounded in the staged diff, without
  re-prompting; the scope alone does not switch it out of its default
  message-only mode). Expect back: message + rationale, then the commit SHA.
- **REQUIRED FOR PRS:** Use `g0ld2k-skills:pr-generator`.
  Pass: the base branch when this run already selected one (stacked or
  integration-branch units — the generator uses it instead of detecting);
  exact test commands actually run; the recorded approval scope covering PR
  creation/update AND pushing the branch (creating a PR runs `git push`).
  Expect back: title/body draft, then the created/updated PR URL — publish
  without re-prompting when the scope covers it.
- **REQUIRED AFTER PR OPEN:** Use `g0ld2k-skills:pr-closeout-loop` when the user asks to
  monitor/address/merge or grants merge authority for the run.
  Pass: owner/repo/PR number, target branch, the authorization scope recorded
  in Phase 0 verbatim, any explicit TDD exemption or its absence, and the
  max-wait policy. Expect back: merged (SHA) or a Blocked Report naming the
  failing gate (G1–G7). Do not merge on its behalf.

## Workflow

### Phase 0: Preflight

1. Complete the Prerequisite Gate for the source-truth triage/disposition row
   before reading repository or live state.
2. Read repo instructions (`AGENTS.md`, `CLAUDE.md`, project docs) and current
   user approvals.
3. Check `git status --short --branch`, remotes, current branch/worktree, and
   default branch.
4. Fetch live source truth for referenced issues, PRs, comments, checks, and
   milestones. Treat handoff plans as context until verified.
5. Record unrelated dirty/untracked files and do not stage or rewrite them.
6. Ask only for blocking ambiguity. If the user gave blanket approval to commit,
   push, create PRs, and merge for this run, do not re-prompt at each routine
   publish step.

### Phase 1: Slice The Work

After source truth is available, assign every unit exactly one evidence-backed
disposition: `actionable`, `already satisfied`, `stale/closed`,
`duplicate/superseded`, or `blocked`. Record the evidence (issue/PR state,
commit, check, or file/behavior observation) beside the disposition. Only
`actionable` units enter implementation or publishing. Complete an
already-satisfied unit without code, commit, push, or PR creation; report its
evidence and any separately authorized issue disposition. Mark stale/closed or
duplicate/superseded units terminal without manufacturing implementation work.
A blocked unit gets the exact Blocked Report shape from
`references/conventions.md`.

Before planning or mutating an actionable unit, select its intended lifecycle
and complete the Prerequisite Gate for the full foreseeable closure. Include
`superpowers:systematic-debugging` when the request or source truth already
shows failing checks that require diagnosis.

For each actionable unit, choose the smallest independently reviewable slice:

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

The note must also contain the prerequisite gate's catalog source, exact
qualified required/present/missing lists, the unit disposition and evidence,
and every selected baseline command with its source. Append each observed
result after running that command. Do not write an uncheckable label without
the commands, source, and results.

Use `docs/superpowers/plans/` for repo plans unless project instructions say
otherwise. Keep plans out of focused issue PRs unless the plan itself is part of
the requested deliverable.

### Phase 3: Implement

For each unit:

1. Start from the correct base branch or isolated worktree.
2. Confirm or extend the cached prerequisite closure for the implementation
   row immediately before any implementation side effect.
3. Write or adjust the failing test first when behavior changes.
4. Make the smallest scoped implementation.
5. Run targeted tests. For package, shared, CI, or broad behavior changes,
   select exact commands from the target repository's instructions, task
   runner or package configuration, and applicable CI workflows. Use
   `.github/workflows/validate-skills.yml` only when that file exists in the
   target repository. Record each command's exact source and observed result
   in the execution note; never report only a label.
6. Preserve unrelated local work and generated artifacts outside the unit.

For mechanical-only work, define a measurable guard first: test inventory,
`rg` assertion, lint failure, file count, or equivalent.

### Phase 4: Simplify And Commit

1. Review `git diff` and `git diff --staged`.
2. Confirm the cached prerequisite closure includes
   `g0ld2k-skills:simplify` before invoking it for a non-trivial change.
3. Address valid in-scope medium/high findings; use judgment on lows.
4. Re-run affected validation after simplify edits.
5. Stage only intended files.
6. Confirm the cached prerequisite closure includes
   `g0ld2k-skills:commit-message` before invoking it; if blanket approval is
   active, commit after verifying the message is grounded in the staged diff.

### Phase 5: PR, Review, CI, Merge

1. Confirm the cached prerequisite closure includes
   `g0ld2k-skills:pr-generator` before using it for a PR title/body. Include
   exact tests actually run.
2. Push and create/update the PR when approval covers the publish step.
3. Confirm the cached prerequisite closure includes the transitive closeout set
   (`g0ld2k-skills:pr-closeout-loop`, `g0ld2k-skills:pr-comment-review`) and any
   active conditional row, including `superpowers:systematic-debugging` for a
   known failing-check diagnosis, before handing off. Treat its Blocked Report
   as this workflow's blocker, not as license to merge manually.
4. After merge, fetch the default branch before starting the next unit.

## Guardrails

- Do not invent issue details, test results, approvals, or remote state.
- Do not bundle unrelated fixes because they are nearby.
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
- "The user said merge, so I can check gates myself instead of deferring to
  `g0ld2k-skills:pr-closeout-loop`."

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

## References

- references/conventions.md for capability ladder, temp files, external-text, and Blocked Report conventions.
