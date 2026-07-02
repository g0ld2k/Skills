---
name: pr-closeout-loop
description: Use when a GitHub pull request or branch already exists and the user wants unattended closeout for review feedback, CI failures, stale approval, or merge readiness.
---

# PR Closeout Loop

## Goal

Close out an existing PR or branch: fetch current feedback, fix only valid
actionable items, validate locally, run quality review for meaningful changes,
commit and push covered work, reply to review threads, monitor CI/review state,
and merge only when authorized gates pass.

This is the executor skill. If the user is still choosing branches, integration
strategy, approval scope, or multi-PR orchestration, use
`integration-branch-orchestrator` first.

## Inputs

Establish before starting:
- PR owner/repo/number, current branch, target branch, and current head SHA.
- Approval signal, including which reviewer identity or reaction counts. Default
  Codex signal: the reaction on the PR description/body changes from eyes to
  thumbs-up. This is not a commit-specific reaction.
- Approval surface: current head SHA plus current PR body.
- User authorization scope for committing, pushing, replying, resolving threads,
  and merging.
- Merge target and method. Default method is a normal merge commit unless the
  user or repository requires another method.
- Max wait policy for repeated no-progress polling states.

## Required Companions

Use these skills when available:
- `pr-comment-review` for fetching every comment and reply in unresolved review
  threads, triaging, fixing, validating, replying to, and resolving PR review
  feedback.
- `simplify` after non-trivial changes before committing.
- `commit-message` before creating commits.
- CI-fix or debugging skills when required checks fail.

Use Superpowers planning only for ambiguous or multi-step implementation work.
Do not require full planning artifacts for small PR comment fixes, reply-only
actions, or straightforward CI patches.

## Loop

1. Preflight.
   - Confirm repo, branch, PR, target branch, head SHA, working tree state, and
     PR body.
   - Fetch latest remote state when the user asked for the latest PR state.
   - Do not stage, commit, overwrite, or discard unrelated local/user changes.

2. Fetch current PR state.
   - Fetch unresolved review threads, including all comments and replies in
     each unresolved thread, plus relevant issue comments, latest reviews,
     check/status rollup, approval signal, and mergeability metadata.
   - Do not rely on helpers that return only top-level review comments unless
     another fetch covers replies in unresolved threads.
   - Treat already-replied old threads as context unless they contain fresh
     actionable feedback.

3. Triage feedback.
   - Classify each unresolved comment as valid, partial, invalid, unclear, or
     conflicting.
   - Decide fix, reply-only, or discuss.
   - Prefer the smallest safe in-scope fix. Stop for human input when feedback
     is unclear or conflicting.

4. Implement valid in-scope fixes.
   - Make narrow edits for approved or loop-authorized fix items only.
   - Run targeted validation, then the repository's local test suite.
   - Local tests are required before merge in this workflow. If the suite cannot
     run or does not exist, block unless the user explicitly changes the gate.

5. Run `simplify` for non-trivial changes.
   - Non-trivial means logic, behavior, tests, CI, package, workflow, public
     contract, or meaningful docs/process changes.
   - In unattended loop runs, automatically address valid in-scope medium/high
     findings only when the user or calling workflow pre-authorized that
     selection policy.
   - Without pre-authorization, present findings for selection before editing.
   - Low findings are optional; mention notable deferred low findings.
   - Re-run affected validation after simplify edits.

6. Commit and push.
   - Stage only intended files.
   - Use `commit-message`.
   - Commit and push only when the user's authorization for this loop covers it.

7. Reply to and resolve review threads.
   - Re-check each target thread is still unresolved before posting.
   - Reply with what changed and what validation ran.
   - Default resolve mode is `after-fixed-reply`: after applying and validating
     a fix, reply to the thread and resolve it automatically.
   - Do not resolve invalid, unclear, conflicting, or declined feedback unless
     the reply explains why and the active policy allows resolution.

8. Monitor review, CI, and approval.
   - Approval is fresh only when it applies to the current head SHA and current
     PR body. New commits or material PR-body edits make approval stale.
   - For the default Codex signal, poll PR description/body reactions for the
     eyes-to-thumbs-up transition; do not look for a commit reaction.
   - Required remote checks must be green for the current head.
   - If new actionable feedback appears, restart at step 2.
   - If checks fail, inspect logs/artifacts through available GitHub, CI
     provider, or MCP tools before editing.
   - If no review/check/build-log progress appears across the max wait window,
     block and report the last observed state.

9. Merge or block.
   - Merge only when every merge gate below is satisfied.
   - If the user gave blanket approval to merge into the current target branch,
     merge there without asking again after gates pass.
   - If merge authorization is absent or ambiguous, ask before merging.
   - Do not merge into a protected/default branch unless that exact promotion is
     authorized.
   - Use a normal merge commit when the method is unspecified. Do not default to
     squash or rebase.

## Merge Gates

All gates must pass before merging:
- Fresh approval covers the current head SHA and current PR body.
- Required remote checks are green for the current head.
- The repository's local test suite passed in this loop.
- No unresolved actionable review feedback remains.
- Fixed review threads were replied to and resolved according to policy.
- The branch is mergeable and up to date enough for the repository's rules.
- No unrelated local/user changes are staged, committed, overwritten, or hidden.
- The user's authorization covers this target branch and merge method.

## Approval Freshness

Approval covers a review surface, not just a PR number. The surface is the
current head SHA plus the current PR body. Approval is stale after a new commit,
a material PR-body edit, or any user-defined surface change.

When freshness is unclear, fetch current PR metadata and wait for fresh approval
instead of relying on an older signal.

## Blocking Conditions

Block instead of waiting or merging when:
- approval is stale or absent;
- required local or remote validation fails;
- CI/log artifacts are unavailable and no local reproduction is possible;
- feedback is invalid, unclear, or conflicting and policy does not allow
  resolution;
- thread replies, thread resolution, pushing, fetching PR state, or merging is
  impossible with available tools;
- unrelated local/user changes would be affected.

## Output

Report:
- comments fetched and triaged;
- fixes, reply-only decisions, and deferred items;
- validation and simplify results;
- commits pushed;
- replies posted and threads resolved or intentionally left unresolved;
- current approval, CI, mergeability, and merge result or blocker.
