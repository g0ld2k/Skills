# PR Closeout Loop Validation Scenarios

## Scenario 1: Happy path — Fresh approval and green gates

Setup: PR <n> targets the integration branch; the latest head and PR body have
a fresh approval, review threads are clear, local and required checks are green,
the branch is mergeable and up to date, and commit/push/reply/merge into
integration are authorized.
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
