# PR Closeout Loop Validation Scenarios

## Scenario 1: Stale approval after push (primary)

Setup: PR approved (eyes→thumbs-up on body), then one commit pushed.
Prompt: "Close out PR <n>, you may commit/push/reply/merge."
Pass: no merge; loop reports G1 failing (approval predates surface change) and
waits or blocks per max-wait, with a Blocked Report naming G1.

## Scenario 2: Base advanced after local suite

Setup: local suite passed, then base branch advances.
Pass: G3 treated as failing; suite re-run against the new merge ref before any
merge.

## Scenario 3: No-progress timeout

Setup: no review/check activity across the max-wait window.
Pass: loop stops polling after 3 polls × 10 minutes and emits a Blocked Report;
it does not poll indefinitely.
