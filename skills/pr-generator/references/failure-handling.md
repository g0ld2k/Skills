# Failure Handling

## Principle

When publish/update fails, report exact failure and one concrete next step.

## Common Failures

### `gh auth status` fails

Action:
- Ask user to authenticate via `gh auth login`.
- Retry preflight before any PR action.

### Push rejected (non-fast-forward or no upstream)

Action:
- Show git error.
- Re-inventory the remote ref and rebuild the publish fingerprint.
- Resolve the history or permission problem, obtain fresh approval when the
  fingerprint changed, then retry the approved-OID refspec from
  `publish-safety.md`.

### Base branch not found

Action:
- Re-run base detection.
- Confirm remote default branch or explicitly ask user for base branch.

### PR already exists

Action:
- Re-inventory the new PR and all fingerprint inputs.
- Display an update fingerprint and obtain update-specific approval before any
  edit; create authority does not cover the concurrent PR.

### Validation/test command failed

Action:
- Report failing command and relevant test target.
- Do not claim success.
- Ask whether to continue with known failures noted in PR body.

## Error Reporting Format

Use this structure:

1. Failed command
2. Key stderr line(s)
3. Likely cause
4. Next action

Keep it concise and actionable.
