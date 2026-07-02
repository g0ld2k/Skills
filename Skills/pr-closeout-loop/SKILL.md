---
name: pr-closeout-loop
description: Use when an existing GitHub pull request, or the current branch's identifiable PR, needs unattended closeout for review feedback, CI failures, stale approval, or merge readiness.
---

# PR Closeout Loop

## Goal

Close out an existing PR: fetch current feedback, fix only valid
actionable items, validate locally, run quality review for meaningful changes,
commit and push covered work, reply to review threads, monitor CI/review state,
and merge only when authorized gates pass.

This is the executor skill. If the user is still choosing branches, integration
strategy, approval scope, PR creation, or multi-PR orchestration, use
`integration-branch-orchestrator` first. If only a branch exists and no PR can be
identified, create or retarget a PR first, or block for topology setup.

## Inputs

Establish before starting:
- PR owner/repo/number, current branch, target branch, current head SHA, and PR
  head repository/ref.
- Approval signal, including which reviewer identity or reaction counts. Default
  Codex signal: the reaction on the PR description/body changes from eyes to
  thumbs-up. This is not a commit-specific reaction.
- Approval surface: current head SHA, current PR body, current target/base
  branch, and current base ref, merge-base, or computed diff.
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
  - In unattended mode, use it only when the user or calling workflow
    pre-authorized the specific coding and reply-posting scope.
  - Without pre-authorization, follow its normal approval gates before coding or
    posting replies.
- `simplify` after non-trivial changes before committing.
- `commit-message` before creating commits.
- CI-fix or debugging skills when required checks fail.

Use Superpowers planning only for ambiguous or multi-step implementation work.
Do not require full planning artifacts for small PR comment fixes, reply-only
actions, or straightforward CI patches.

## Loop

1. Preflight.
   - Confirm repo, branch, PR, target branch, head SHA, PR head repository/ref,
     working tree state, and PR body.
   - Fetch latest remote PR state and sync the local checkout to the exact
     current PR head before editing. Block if that cannot be done safely.
   - Do not stage, commit, overwrite, or discard unrelated local/user changes.

2. Fetch current PR state.
   - Fetch unresolved review threads, including all comments and replies in
     each unresolved thread, plus PR conversation comments, latest reviews,
     check/status rollup, approval signal, and mergeability metadata.
   - Do not rely on helpers that return only top-level review comments unless
     another fetch covers replies in unresolved threads.
   - Triage every unresolved thread as fresh actionable feedback, already
     addressed and eligible for resolution, or blocked according to the active
     resolution policy.

3. Triage feedback.
   - Classify each unresolved review-thread comment, PR conversation comment,
     and latest review body/state as valid, partial, invalid, unclear, or
     conflicting.
   - Treat `CHANGES_REQUESTED` as blocking until superseded by an eligible newer
     approval, dismissed according to repository policy, or addressed through
     the active feedback policy.
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
   - Use `commit-message` to generate the Conventional Commit message from the
     staged diff.
   - In unattended mode, treat loop authorization for commits as pre-approval to
     use the generated message and commit, as long as the message is supported by
     the staged diff and no companion skill explicitly blocks.
   - Commit and push only when the user's authorization for this loop covers it.
   - Push to the recorded PR head repository/ref, then verify the pushed commit
     is the PR's current head before replying or merging.

7. Reply to feedback and resolve review threads.
   - Re-fetch each target thread's current comments and replies before posting
     or resolving. If contents changed since triage, restart at step 2.
   - Re-check each target thread is still unresolved before posting.
   - Reply with what changed and what validation ran.
   - For actionable PR conversation comments, reply or acknowledge with the fix,
     validation, or rationale. Treat a conversation comment as addressed only
     when the acknowledgement names the specific comment it addresses and appears
     after re-fetching and triaging the latest PR conversation comments.
   - For actionable review-level bodies without an inline thread, reply through
     the appropriate PR review or conversation channel and treat the feedback as
     addressed only when the acknowledgement names the specific review it
     addresses and appears after re-fetching and triaging the latest reviews.
   - Default resolve mode is `after-fixed-reply`: after applying and validating
     a fix, reply to the thread and resolve it automatically.
   - Do not resolve invalid, unclear, conflicting, or declined feedback unless
     the reply explains why and the active policy allows resolution.

8. Monitor review, CI, and approval.
   - Approval is fresh only when it applies to the current head SHA, current PR
     body, current target/base branch, and current base ref, merge-base, or
     computed diff. New commits, material PR-body edits, base-branch changes, or
     base-ref changes make approval stale.
   - For the default Codex signal, poll PR description/body reactions for the
     eyes-to-thumbs-up transition after the latest surface-changing event; do
     not treat an older thumbs-up as fresh approval, and do not look for a
     commit reaction.
   - Required remote checks must be green for the current head against the
     current base or merge ref. After base-ref changes, require fresh checks,
     a merge-ref validation, or an explicit rerun before merge.
   - If new actionable feedback appears, restart at step 2.
   - If checks fail, inspect logs/artifacts through available GitHub, CI
     provider, or MCP tools before editing.
   - If no review/check/build-log progress appears across the max wait window,
     block and report the last observed state.

9. Merge or block.
   - Immediately before merging, fetch current PR state again and re-evaluate
     feedback, approval freshness, required checks, base ref, mergeability, and
     unrelated local/user changes.
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
- Fresh approval covers the current target/base branch and current base ref,
  merge-base, or computed diff.
- Required remote checks are green for the current head against the current base
  or merge ref, including after base-ref changes.
- The repository's local test suite passed in this loop.
- No unresolved actionable review-thread, review-level, or PR conversation
  feedback remains.
- Fixed review threads were replied to and resolved according to policy, and
  fixed review-level and PR conversation comments were acknowledged according to
  policy.
- The branch is mergeable and up to date enough for the repository's rules.
- A final pre-merge refresh confirmed the gates still pass.
- No unrelated local/user changes are staged, committed, overwritten, or hidden.
- The user's authorization covers this target branch and merge method.

## Approval Freshness

Approval covers a review surface, not just a PR number. The surface is the
current head SHA plus the current PR body, target/base branch, and current base
ref, merge-base, or computed diff. Approval is stale after a new commit, a
material PR-body edit, a base-branch change, a base-ref change, or any
user-defined surface change.

When freshness is unclear, fetch current PR metadata and wait for a fresh signal
created after the latest surface-changing event instead of relying on an older
signal.

## Blocking Conditions

Block instead of waiting or merging when:
- approval is stale or absent after the wait policy is exhausted;
- required local validation fails;
- required remote validation fails after CI triage/fix attempts or the wait
  policy is exhausted;
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
