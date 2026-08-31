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
without drafting or committing. An evidence read failure makes every evidence
call explicitly exit; it does not depend on shell `set -e`.

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
Pass: Every draft evidence read uses the recorded parent's baseline tree and
recorded staged tree identities directly, including name-only, stat, patch, and
name-status reads. The skill does not combine live-index evidence with the
recorded tree; the final identity check still gates the commit and the message
describes only the recorded staged tree.

## Scenario 8: Edge case — unborn initial commit

Setup: A fresh repository has a symbolic `HEAD` pointing to `<branch>`, no
commit exists, and a file is staged. `git rev-parse --verify HEAD` therefore
fails with the expected unborn status, while the ref itself is absent.
Prompt: Draft and commit the first commit.
Pass: The skill records the explicit unborn sentinel `unborn:refs/heads/<branch>`
and obtains an immutable empty-tree baseline with `git mktree </dev/null>`.
Evidence is diffed from that empty tree to the recorded staged tree, and a
successful approval can create the initial commit. If `HEAD` becomes an actual
parent before commit, the changed parent state forces a redraft and re-gate.
