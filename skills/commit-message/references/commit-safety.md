# Commit Safety

Use this procedure to create and revalidate a draft identity while preserving
normal Git behavior.

## Snapshot

1. Confirm `git rev-parse --is-inside-work-tree` succeeds and returns `true`.
2. Resolve the per-worktree merge marker with `git rev-parse --git-path
   MERGE_HEAD`. Block if that path exists; a branch or tag named `MERGE_HEAD`
   is not a merge marker.
3. Preserve the exit status of `git diff --cached --quiet`: `0` means no staged
   changes, `1` means continue, and every other status is a Git error.
4. Record `draft_parent` from `git rev-parse --verify HEAD`. For an initial
   commit, confirm `HEAD` is symbolic and its target ref is absent, record
   `unborn:<ref>`, and create the repository-format empty-tree OID with
   `git mktree </dev/null>`. Other lookup failures block. A normal parent is
   also the evidence base.
5. Record `staged_tree` with `git write-tree`.
6. Read the snapshot once with `git --no-pager diff --no-color --no-ext-diff
   --no-textconv --patch-with-stat --summary <evidence-base> <staged-tree>`.
   Capture and report failures. Do not combine later live-index reads with this
   evidence; the object-to-object diff prevents index ABA changes from mixing
   snapshots.

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
