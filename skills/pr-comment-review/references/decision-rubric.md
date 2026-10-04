# Decision Rubric

Use this rubric when feedback is ambiguous. Judge the complete conversation,
including replies, against current code.

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

## Structured triage when useful

Triage the thread's final state: read replies, not just the root comment.

When a helper or report needs structured triage, useful fields are:
- `comment_id`
- `thread_id` (required by `post_pr_replies.sh` for the per-reply resolved
  check; carry it through from the fetch step)
- `file_line`
- `validity`
- `priority`
- `decision`
- `planned_action`
- `draft_reply`

A brief prose decision is enough for straightforward feedback. The posting
helper requires only `thread_id`, `comment_id`, and a nonempty reply `body`;
the other triage fields support reasoning and are not a mandatory report schema.
