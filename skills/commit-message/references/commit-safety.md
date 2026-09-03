# Commit Safety

Read this reference for an initial commit, and always before committing in
`message+commit` mode. The snapshot commands themselves live in `SKILL.md`
step 1.

## Snapshot notes

- The merge marker is the per-worktree path from `git rev-parse --git-path
  MERGE_HEAD`; a branch or tag named `MERGE_HEAD` is not a merge marker.
- For an initial commit, `git rev-parse --verify HEAD` fails. Confirm `HEAD` is
  symbolic and its target ref is absent, record `draft_parent` as
  `unborn:<ref>`, record the empty-tree OID from `git mktree </dev/null` as the
  separate `evidence_base`, and pass that OID to `git diff`. The sentinel is
  identity only. Any other lookup failure blocks.

## Revalidate and commit

Resolve the effective hooks directory from `core.hooksPath` or `git rev-parse
--git-path hooks`. In `message+commit`, executable `pre-commit`,
`prepare-commit-msg`, or `commit-msg` hooks are potentially identity-mutating
unless repository policy proves otherwise. Block automated exact-identity
commit when any are active; require a human or policy-specific path that runs
the hooks and presents any resulting tree/message for fresh authorization.
Never bypass them with `--no-verify`.

Otherwise create a unique message file under the shared temp-file rule,
canonicalized with one final LF, and arrange cleanup on success, failure, and
interruption. Immediately before committing:

1. Repeat the staged-status check, parent resolution, and `git write-tree`.
2. Compare the current parent and tree with the approved draft identity.
3. Resolve and check the per-worktree merge marker again.

Any mismatch deletes the temporary message, discards the draft, and returns to
inventory and authorization. A porcelain `git commit` cannot take the approved
parent and tree as operands, so do not use it for exact-identity automation.
Instead:

1. Create a candidate with `git commit-tree <approved-tree> [-p
   <approved-parent>] -F <message-file>`. This binds the immutable tree and
   parent directly and performs no message cleanup. Initial commits omit `-p`.
2. Read the candidate object and require its tree, parent list, and message
   bytes to equal the approved identity. Do not move a ref on mismatch.
3. Atomically install it with `git update-ref <approved-head-ref>
   <candidate-oid> <approved-parent-oid>`. For an unborn ref, use the all-zero
   old OID; for detached HEAD, target `HEAD`. A compare-and-swap failure leaves
   the live ref untouched and returns to inventory.

Resolve and freeze the symbolic head ref before authorization. Block this
plumbing path when repository policy requires a porcelain-only hook lifecycle;
an unreachable candidate object after a failed ref update is not a successful
commit. After success, read the installed SHA, tree, parents, and message from
Git before reporting them.
