# Commit Safety

Read this reference for an initial commit, and always before committing in
`message+commit` mode. The snapshot commands themselves live in `SKILL.md`
step 1.

## Snapshot notes

- The merge marker is the per-worktree path from `git rev-parse --git-path
  MERGE_HEAD`; a branch or tag named `MERGE_HEAD` is not a merge marker.
- For an initial commit, `git rev-parse --verify HEAD` fails. Confirm `HEAD` is
  symbolic and its target ref is absent, record `draft_parent` as
  `unborn:<ref>`, and use the empty tree from `git mktree </dev/null` as the
  evidence base for the diff. Any other lookup failure blocks.

## Revalidate and commit

Create a unique message file under the shared temp-file rule and arrange
cleanup on success, failure, and interruption. Immediately before committing:

1. Repeat the staged-status check, parent resolution, and `git write-tree`.
2. Compare the current parent and tree with the approved draft identity.
3. Resolve and check the per-worktree merge marker again.

Any mismatch deletes the temporary message, discards the draft, and returns to
inventory and authorization. When all checks match, run normal `git commit -F
<message-file>` so repository hooks and policy remain active. If it fails,
report the command, status, and Git error without commit metadata. After
success, read the SHA and subject from Git before reporting them.
