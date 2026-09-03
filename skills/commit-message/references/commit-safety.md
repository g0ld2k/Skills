# Commit Safety

Read this reference for an initial commit, and always before committing in
`message+commit` mode. The snapshot commands themselves live in `SKILL.md`
step 1.

## Snapshot notes

- Resolve these per-worktree paths with `git rev-parse --git-path`: `MERGE_HEAD`,
  `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `sequencer`, `rebase-merge`, and
  `rebase-apply`. An existing marker blocks ordinary commit drafting and
  publishing; a branch or tag with the same name is not a marker.
- For an initial commit, `git rev-parse --verify HEAD` fails. Confirm `HEAD` is
  symbolic and its target ref is absent, record `draft_parent` as
  `unborn:<ref>`, record the empty-tree OID from `git mktree </dev/null` as the
  separate `evidence_base`, and pass that OID to `git diff`. The sentinel is
  identity only. Any other lookup failure blocks.

## Revalidate and commit

Resolve the effective hooks directory from `core.hooksPath` or `git rev-parse
--git-path hooks`. In `message+commit`, executable `pre-commit`,
`prepare-commit-msg`, or `commit-msg` hooks may change identity, while an
executable `post-commit` hook is required lifecycle behavior. Unless repository
policy proves the applicable hook irrelevant, block automated exact-identity
commit and require a human or policy-specific path that runs it and presents
any resulting tree/message for fresh authorization. Never bypass hooks.

Resolve `commit.gpgSign`, `user.signingKey`, `gpg.format`, and applicable
repository signing policy before authorization. Freeze the required signing
mode and key with the draft identity. When signing is required, construct with
the approved `commit-tree -S[<key>]` option and require `git verify-commit` to
validate the candidate before moving a ref. Block if policy is unresolved, the
signer is unavailable, or verification fails.

Otherwise create a unique message file under the shared temp-file rule,
canonicalized with one final LF, and arrange cleanup on success, failure, and
interruption. Immediately before committing:

1. Repeat the staged-status check, parent resolution, operation-marker checks,
   HEAD symbolic/detached resolution, and `git write-tree`.
2. Compare the current parent and tree with the approved draft identity.
3. Require the HEAD state and exact symbolic ref, if any, to match the approved
   state.

Any mismatch deletes the temporary message, discards the draft, and returns to
inventory and authorization. A porcelain `git commit` cannot take the approved
parent and tree as operands, so do not use it for exact-identity automation.
Instead:

1. Create a candidate with `git commit-tree <approved-tree> [-p
   <approved-parent>] [-S[<approved-key>]] -F <message-file>`. This binds the
   immutable tree and parent directly and performs no message cleanup. Initial
   commits omit `-p`.
2. Read the candidate object and require its tree, parent list, and message
   bytes to equal the approved identity. Do not move a ref on mismatch.
3. Atomically install it with `git update-ref <approved-head-ref>
   <candidate-oid> <approved-parent-oid>`. For an unborn ref, use the all-zero
   old OID. For an approved detached state, recheck that HEAD is still detached
   and use `git update-ref --no-deref HEAD <candidate-oid>
   <approved-parent-oid>` so a late symbolic transition cannot move a branch.
   A compare-and-swap failure leaves the live ref untouched and returns to
   inventory.

Resolve and freeze symbolic-versus-detached HEAD plus any symbolic ref before
authorization. Block this plumbing path when repository policy requires a
porcelain-only lifecycle. An unreachable candidate after failed ref update is
not a successful commit. After success, read the installed SHA, tree, parents,
message, and required signature from Git before reporting them.
