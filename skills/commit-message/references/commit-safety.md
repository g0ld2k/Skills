# Commit Safety

Read this reference for an initial commit or before committing in
`message+commit` mode. Snapshot commands and operation markers live in
`SKILL.md` step 1.

## Snapshot notes

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
interruption. Automated installation requires symbolic HEAD; detached
`message+commit` blocks because Git cannot transactionally assert a non-symbolic
HEAD while replacing it. Create and verify the candidate from the approved
identity, then exclusively create the per-worktree index lock returned by `git
rev-parse --git-path index.lock`. Never replace or remove another process's
lock. Retain the owned lock through ref installation.

While holding both locks:

1. Copy the now-locked live index to a private file. Repeat the staged-status
   check with `--no-relative --ignore-submodules=none`; run `git write-tree`
   against that copy via `GIT_INDEX_FILE`. Repeat parent, operation-marker, and
   symbolic-HEAD resolution.
2. Compare the current parent and tree with the approved draft identity.
3. Require the HEAD state and exact symbolic ref, if any, to match the approved
   state.

Any mismatch releases owned locks, deletes the temporary message, discards the
draft, and returns to inventory and authorization. A porcelain `git commit`
cannot take the approved parent and tree as operands, so use this plumbing
path:

1. Before locking, create a candidate with `git commit-tree <approved-tree>
   [-p <approved-parent>] [-S[<approved-key>]] -F <message-file>`. This binds
   the immutable tree and parent directly. Initial commits omit `-p`.
2. Before locking, read the candidate object and require its tree, parent list,
   and message bytes to equal the approved identity.
3. While holding the index lock, use one `git update-ref --stdin` transaction
   containing `symref-verify HEAD <approved-head-ref>` and `update
   <approved-head-ref> <candidate-oid> <approved-parent-oid>`. For an unborn
   ref, use the all-zero old OID. The transaction atomically binds symbolic HEAD
   and its target; the index lock excludes normal operation-state changes.
   Release the owned lock after the transaction. Failure leaves refs untouched
   and returns to inventory.

Resolve and freeze symbolic-versus-detached HEAD plus any symbolic ref before
authorization. Block this plumbing path when repository policy requires a
porcelain-only lifecycle. An unreachable candidate after failed ref update is
not a successful commit. After success, read the installed SHA, tree, parents,
message, and required signature from Git before reporting them.
