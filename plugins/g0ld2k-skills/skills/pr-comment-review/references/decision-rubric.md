# Decision Rubric

Use this rubric for each unresolved review thread, judged on its final state (root comment plus all replies).

## Validity

- `valid`: Comment is correct and should be addressed.
- `partial`: Concern is directionally right but details/solution need adjustment.
- `invalid`: Concern is not applicable, stale, already addressed, or technically incorrect.
- `unclear`: intent cannot be determined from the thread; decision must be `discuss`.
- `conflicting`: contradicts another active comment or review; decision must be `discuss`.

## Priority

- `high`: correctness bug, security risk, data loss risk, misleading behavior/spec claim.
- `medium`: maintainability, test coverage gaps, error handling, reliability edge cases.
- `low`: style preference, naming preference, optional refactor.

## Decision

- `fix`: make a code change.
- `reply`: no code change, explain rationale or current behavior.
- `discuss`: requires product/architectural decision or conflicting feedback resolution.

## Required Triage Fields

Triage the thread's final state: read replies, not just the root comment.

For consistency, output:
- `comment_id`
- `thread_id` (required by `post_pr_replies.sh` for the per-reply resolved
  check; carry it through from the fetch step)
- `file_line`
- `validity`
- `priority`
- `decision`
- `planned_action`
- `draft_reply`
