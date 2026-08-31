# Commit Message Validation Scenarios

## Scenario 1: Happy path — successful commit

Setup: A repository has staged changes, `HEAD` is `<draft_parent>`,
`git write-tree` records `<draft_tree>`, and both identities remain stable
through approval. The applicable commit gate passes.
Prompt: Draft and commit a Conventional Commit message.
Pass: The skill shows the recorded parent and staged tree with the draft,
rechecks both immediately before normal `git commit -F`, cleans the message
file, and reports SHA and subject only after success.

## Scenario 2: Edge case — no staged changes

Setup: `git diff --cached --quiet` exits `0`.
Prompt: Generate a commit message.
Pass: The skill asks for the intended files to be staged and neither drafts nor
commits.

## Scenario 3: Edge case — Git error

Setup: The staged-status check, parent resolution, `git write-tree`, or an
evidence read fails with an error status.
Prompt: Generate a commit message.
Pass: The skill reports the failing command, status, and Git error, then stops
without drafting or committing. The single evidence command captures its
status explicitly and explicitly exits on an evidence read failure; it does not
depend on shell `set -e`.

## Scenario 4: Adversarial — index drift during approval

Setup: The staged tree changes after the draft is shown and before `git commit`
is invoked.
Prompt: Commit the previously approved message.
Pass: The skill identifies the changed staged tree, discards the stale draft,
recollects evidence from the new recorded parent and staged tree, and runs the
same gate for the new identities and message. Attended approval is requested
again; recorded preauthorization is re-evaluated.

## Scenario 5: Edge case — commit failure or interruption

Setup: `git commit -F` fails, or the process is interrupted after the temporary
message file is created.
Prompt: Commit and report the result.
Pass: Cleanup removes the message file, and interruption stops the workflow
with a nonzero status. A failure reports the command, status, and Git error
without reporting a SHA or subject as if a commit succeeded.

## Scenario 6: Adversarial — commit-parent drift with unchanged staged tree

Setup: The draft records parent `<old_parent>` and staged tree
`<unchanged_tree>`. During approval, another commit advances `HEAD` to
`<new_parent>` while the index still writes `<unchanged_tree>`.
Prompt: Commit the approved message after the repository advances.
Pass: The skill compares the current parent with the recorded parent as well
as comparing the staged trees. It detects commit-parent drift even though the
staged tree is unchanged, discards the old draft, collects evidence against
`<new_parent>` and the recorded staged tree, and re-applies the approval gate.
It never invokes `git commit` with the old parent-bound approval.

## Scenario 7: Adversarial — ABA race in evidence collection

Setup: `git write-tree` records staged tree `<recorded_tree>`. While evidence
is being collected, the index briefly changes to another tree and then returns
to `<recorded_tree>` before the commit check. The live index would therefore
produce an ABA mismatch between separate `git diff --cached` reads.
Prompt: Draft and commit while another process changes and restores the index.
Pass: One `git diff --no-color --no-ext-diff --no-textconv
--patch-with-stat --summary <recorded_parent> <recorded_tree>` command supplies
the evidence from the recorded parent commit and staged tree. The skill does
not combine live-index evidence with the recorded tree; the final identity
check still gates the commit and the message describes only the recorded
staged tree. Binary changes remain bounded metadata. The command uses the
effective Git object/configuration view for that single command; concurrent
replacement refs, repository-local attributes/configuration, and hooks are
outside this normal-Git snapshot guarantee.

## Scenario 8: Edge case — unborn initial commit

Setup: A fresh repository has a symbolic `HEAD` pointing to `<branch>`, no
commit exists, and a file is staged. `git rev-parse --verify HEAD` therefore
fails with the expected unborn status, while the ref itself is absent.
Prompt: Draft and commit the first commit.
Pass: The skill records the explicit unborn sentinel `unborn:refs/heads/<branch>`
and creates the repository-format-specific empty-tree OID with
`git mktree </dev/null>` as the evidence base. Evidence is diffed from that
empty tree to the recorded staged tree, and a successful approval can create
the initial commit. If `HEAD` becomes an actual parent before commit, the
changed parent state forces a redraft and re-gate.

## Scenario 9: Adversarial — baseline lookup race

Setup: The draft records `<draft_parent>`, and a separate operation may move
`HEAD` while the draft is being prepared. The recorded parent remains the
identity being approved.
Prompt: Draft and commit while `HEAD` may advance during evidence collection.
Pass: The normal evidence base is the recorded `<draft_parent>` commit OID
itself, and an unborn draft uses the immutable empty-tree OID. The final
recheck likewise records `<current_parent>` and uses that commit OID if it is
present. No separate live baseline lookup occurs, so any parent change is
detected and re-gated.

## Scenario 10: Edge case — merge in progress

Setup: `git rev-parse --git-path MERGE_HEAD` resolves the per-worktree
pseudoref path, and that path exists.
Prompt: Generate a commit message while a merge is in progress.
Pass: The skill reports that a merge is in progress and stops before drafting
or committing. It does not model multi-parent merges. A missing pseudoref path
continues, while a Git error resolving the path is reported and stops. A branch
or tag named `MERGE_HEAD` does not trigger the guard. The same check is the
repeated merge gate immediately before commit, after the parent/tree recheck.
