---
name: work-request-orchestration
description: Use when turning GitHub issues, milestones, epics, work requests, or external plans into an implementation, validation, PR, review, and merge workflow.
license: MIT
disable-model-invocation: true
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
- **REQUIRED BEFORE COMMIT:** Use `simplify` for non-trivial code changes
  (non-trivial per `pr-closeout-loop`'s definition: logic, behavior, tests, CI,
  package, workflow, public-contract, or meaningful docs/process changes).
  Pass: the recorded unattended selection policy when blanket approval is
  active (default: auto-address valid in-scope medium/high findings without
  re-prompting). Expect back: numbered findings applied per that policy, or
  presented for user selection in attended runs.
- **REQUIRED FOR COMMITS:** Use `commit-message`.
  Pass: staged diff, an explicit `message+commit` mode request, plus the
  recorded approval scope (blanket commit approval means commit with the
  generated message once it is grounded in the staged diff, without
  re-prompting; the scope alone does not switch it out of its default
  message-only mode). Expect back: message + rationale, then the commit SHA.
- **REQUIRED FOR PRS:** Use `pr-generator`.
  Pass: the base branch when this run already selected one (stacked or
  integration-branch units — the generator uses it instead of detecting);
  exact test commands actually run; the recorded approval scope covering PR
  creation/update AND pushing the branch (creating a PR runs `git push`).
  Expect back: title/body draft, then the created/updated PR URL — publish
  without re-prompting when the scope covers it.
- **REQUIRED AFTER PR OPEN:** Use `pr-closeout-loop` when the user asks to
  monitor/address/merge or grants merge authority for the run.
  Pass: owner/repo/PR number, target branch, the authorization scope recorded
  in Phase 0 verbatim, and the max-wait policy. Expect back: merged (SHA) or a
  Blocked Report naming the failing gate (G1–G7). Do not merge on its behalf.

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
3. Hand off to `pr-closeout-loop` with the contract above; treat its Blocked
   Report as this workflow's blocker, not as license to merge manually.
4. Merge gating is owned by `pr-closeout-loop` (G1–G7); this workflow does not
   evaluate its own reduced gate set or merge manually.
5. After merge, fetch the default branch before starting the next unit.

## Guardrails

- Do not invent issue details, test results, approvals, or remote state.
- Do not bundle unrelated fixes because they are nearby.
- Do not merge manually or re-evaluate merge gates; defer to
  `pr-closeout-loop`'s G1–G7 and act only on its Blocked Report.
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
  `pr-closeout-loop`."

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
