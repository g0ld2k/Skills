# Decision Rubric

Use this rubric for each unresolved top-level review comment.

## Validity

- `valid`: Comment is correct and should be addressed.
- `partial`: Concern is directionally right but details/solution need adjustment.
- `invalid`: Concern is not applicable, stale, already addressed, or technically incorrect.

## Priority

- `high`: correctness bug, security risk, data loss risk, misleading behavior/spec claim.
- `medium`: maintainability, test coverage gaps, error handling, reliability edge cases.
- `low`: style preference, naming preference, optional refactor.

## Decision

- `fix`: make a code change.
- `reply`: no code change, explain rationale or current behavior.
- `discuss`: requires product/architectural decision or conflicting feedback resolution.

## Required Triage Fields

For consistency, output:
- `comment_id`
- `file_line`
- `validity`
- `priority`
- `decision`
- `planned_action`
- `draft_reply`
