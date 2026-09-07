# Failure Handling

## Principle

When publish/update fails, report exact failure and one concrete next step.

## Common Failures

### `gh auth status` fails

Action:
- Use an already authenticated GitHub MCP capability if it can perform the operation.
- If no publishing capability works, finish the draft and report publication blocked.
- Request authentication only for the remaining requested operation; retry that operation once available.

### Push rejected (non-fast-forward or no upstream)

Action:
- Show git error.
- Suggest `git pull --rebase` (if appropriate) or resolve branch permissions.
- Re-run `git push -u origin <branch>` after conflict resolution.

### Base branch not found

Action:
- Re-run base detection.
- Confirm remote default branch or explicitly ask user for base branch.

### PR already exists

Action:
- Switch to update mode (`gh pr edit`) instead of `gh pr create`.

### Validation/test command failed

Action:
- Report failing command and relevant test target.
- Do not claim success.
- Complete the draft with the known failures accurately recorded.
- Continue diagnosis or fixes within existing authorization. Publication must satisfy
  its authorization and repository policies; this does not waive posting or merge
  gates in companion workflows. Ask only for a decision those policies require.

## Error Reporting Format

Use this structure:

1. Failed command
2. Key stderr line(s)
3. Likely cause
4. Next action

Keep it concise and actionable.
