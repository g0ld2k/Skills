# PR Closeout Loop Validation Scenarios

## Scenario 1: Happy path — Fresh approval and green gates

Setup: PR <n> targets integration branch <target> at base ref <base_sha>; the
local checkout matches head <head_sha> and has a clean worktree with no unrelated
user changes. Approval created after the latest surface change explicitly covers
that head, the current PR body fingerprint, <target>, and <base_sha>. Required
checks are successful for the current head and base or merge ref, with no later
base-ref change, and the local suite records a pass for <head_sha> against
<base_sha>. Feedback has zero actionable items, no unresolved unclear,
conflicting, or discuss-classified item, no effective `CHANGES_REQUESTED`, and
every fixed thread is replied to and resolved per policy; all fixed review-level
and conversation feedback is acknowledged. The branch is mergeable and up to
date. User authorization covers commit, push, reply, thread resolution, and the
normal merge method into exactly <target>.
Prompt: "Close out PR <n> after all current gates pass."
Pass: loop reports G1–G7 passing, merges the PR with the normal merge method,
and does not promote the integration branch to the protected default branch.

## Scenario 2: Edge case — Base advanced after local suite

Setup: local suite passed, then base branch advances.
Prompt: "Use `pr-closeout-loop` after the base branch advances."
Pass: G3 treated as failing; suite re-run against the new merge ref before any
merge.

## Scenario 3: Adversarial — No-progress timeout

Setup: no review/check activity across the max-wait window.
Prompt: "Use `pr-closeout-loop` while waiting for review and checks."
Pass: loop stops polling after 3 polls × 10 minutes and emits a Blocked Report;
it does not poll indefinitely.
