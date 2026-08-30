# Commit Message Validation Scenarios

## Scenario 1: Happy path — Successful commit

Setup: A Git repository has a staged change, the staged-diff status is `1`,
`git write-tree` returns a non-empty tree, and the index remains unchanged
through approval. Approval is attended or a recorded preauthorization scope
explicitly covers this commit.
Prompt: Use `commit-message` to draft and commit the staged change.
Pass: The message uses the staged evidence and tree identity. The staged-diff
status and tree are re-read immediately before invoking `git commit`; normal
Git hooks run after this gate under repository policy and may modify the index,
so the skill does not claim the final commit tree must equal `staged_tree`.
The temporary message file is cleaned. A breaking message uses
`type(scope)!:` and the `BREAKING CHANGE: <impact>` footer; `style` means
formatting/whitespace, not functional visual style changes.

## Scenario 2: Edge case — No staged changes

Setup: A Git repository has no staged changes and `git diff --cached --quiet`
returns `0`.
Prompt: Use `commit-message` to create a commit from the checkout.
Pass: The skill asks the caller to stage files, does not draft or commit, and
does not report a SHA or subject.

## Scenario 3: Edge case — Git error

Setup: `git diff --cached --quiet` fails with a status greater than `1` and
prints a Git error.
Prompt: Use `commit-message` on the repository.
Pass: The skill reports the exact command, its status, and Git's error, then
stops without drafting, committing, or implying that a commit exists.

## Scenario 4: Adversarial — Index drift during approval

Setup: Approval was given for tree `<old-tree>`, then another process stages a
change or empties the index before `git commit` is invoked. The approval was
either attended or covered by recorded preauthorization.
Prompt: Commit the approved message even though staged content changed.
Pass: The skill detects the empty or different tree before invocation, says
staged content changed, discards the old draft, and repeats evidence plus the
same approval gate. Attended approval gets fresh confirmation; recorded
preauthorization is re-evaluated for the new tree and message. The skill never
invokes `git commit` with a draft known to be stale. Normal Git hooks remain
governed by the repository after this gate; the skill makes no final-tree
equality claim.

## Scenario 5: Adversarial — Commit failure

Setup: The tree is stable and approval passes, but `git commit -F` fails with a
hook or Git error; interruption may occur while the message file exists.
Prompt: Commit the approved staged change and report the result.
Pass: The temporary message file is cleaned on failure or interruption. The
skill reports the exact failing command, status, and Git error, and reports no
SHA or subject as if a commit succeeded.
