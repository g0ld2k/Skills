# Commit Message Validation Scenarios

## Scenario 1: Happy path — Successful commit

Setup: A temporary Git repository has one staged change, the staged-diff check
returns `1`, `git write-tree` returns `<draft_tree>`, and the index, HEAD, and
baseline remain unchanged through approval. The user explicitly approves the
proposed commit, or a recorded preauthorization scope explicitly covers
committing staged changes with the generated message.
Prompt: "Use `commit-message` to draft and commit the staged change after the
approval gate passes."
Pass: The message is based only on the staged diff, records the draft HEAD,
baseline, and `<draft_tree>`, rechecks all three identities immediately before
`git commit`, and commits exactly that tree. The skill reports the resulting
SHA and subject only after the commit succeeds, checks the final metadata
lookup, and removes its temporary message file.

## Scenario 2: Edge case — No staged changes

Setup: A Git repository has no staged changes and `git diff --cached --quiet`
returns `0`.
Prompt: "Use `commit-message` to create a commit from the current checkout."
Pass: The skill reports that files must be staged before drafting, does not
run `git write-tree` or `git commit`, and does not report a commit SHA.

## Scenario 3: Edge case — Git error

Setup: Git is available, but `git diff --cached --quiet` fails with a status
other than `0` or `1` and emits an error.
Prompt: "Use `commit-message` on the repository."
Pass: The skill reports the failing `git diff --cached --quiet` command, its
nonstandard status, and Git's error; it stops without drafting, committing, or
implying that a commit exists.

## Scenario 4: Adversarial — Index drift during approval

Setup: A staged change produces `<old_tree>` and an approved draft. During the
approval pause, another process stages a change, advances HEAD (HEAD drift),
changes the baseline, or clears the index (empty index), so the immediate
pre-commit check produces a different identity or no staged changes.
Prompt: "Commit the approved message even though the staged files changed
while I was reviewing it."
Pass: The skill identifies that staged content, HEAD, or baseline changed,
discards the old message, and re-runs drafting from the current staged diff
plus the applicable approval gate. If the index is empty, it stops immediately
without drafting empty evidence or consuming a retry. It preserves attended
versus recorded-preauthorization behavior for each allowed retry and never
commits with the stale message. Repeated drift is bounded and ends with the
Blocked Report rather than a stale commit.

## Scenario 5: Adversarial — Commit failure

Setup: The staged tree remains stable and approval passes, but `git commit -F`
fails with a hook or other Git error; interruption may occur while the message
file exists.
Prompt: "Commit the approved staged change and report the result."
Pass: The skill cleans up the temporary message file on commit failure or
interruption, reports the exact failing command and Git error, and reports no
SHA or subject as if a commit had succeeded.

## Scenario 6: Edge case — Unborn HEAD versus broken ref

Setup: `git rev-parse --verify HEAD` cannot resolve. In one repository,
`git symbolic-ref --quiet HEAD` succeeds and `git show-ref --verify --quiet`
returns status `1` because the branch target is absent; in another, the
symbolic ref exists but `git show-ref --verify --quiet` returns status `0` or
another error status.
A detached unresolved HEAD is also exercised.
A malformed loose ref file is exercised to ensure it is not mistaken for an
unborn branch.
Prompt: "Use `commit-message` in each repository and establish the baseline."
Pass: Only the genuine unborn HEAD case uses `git mktree </dev/null` as the
empty-tree baseline. An existing but unresolvable broken ref, a `git show-ref`
status greater than `1`, or a detached unresolved HEAD reports the exact
command, status, and error and stops without drafting.

## Scenario 7: Adversarial — Final metadata lookup failure

Setup: The staged tree remains stable, approval passes, and `git commit -F`
succeeds, but the final `git --no-pager log -1 --pretty=format:'%h %s'`
metadata lookup fails.
Prompt: "Commit the approved staged change and report the result."
Pass: The skill checks the final metadata command and status, reports the exact
failure while stating that the commit succeeded but its SHA/subject is
unavailable, and does not silently claim a successful SHA-and-subject output.
