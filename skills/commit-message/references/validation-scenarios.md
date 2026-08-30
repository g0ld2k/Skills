# Commit Message Validation Scenarios

## Scenario 1: Happy path — successful commit

Setup: A repository has staged changes, `git write-tree` is stable through
approval, and the applicable commit gate passes.
Prompt: Draft and commit a Conventional Commit message.
Pass: The skill shows the tree identity with the draft, rechecks it immediately
before normal `git commit -F`, cleans the message file, and reports SHA and
subject only after success.

## Scenario 2: Edge case — no staged changes

Setup: `git diff --cached --quiet` exits `0`.
Prompt: Generate a commit message.
Pass: The skill asks for the intended files to be staged and neither drafts nor
commits.

## Scenario 3: Edge case — Git error

Setup: The staged-status check or `git write-tree` fails with an error status.
Prompt: Generate a commit message.
Pass: The skill reports the failing command, status, and Git error, then stops
without drafting or committing.

## Scenario 4: Adversarial — index drift during approval

Setup: The staged tree changes after the draft is shown and before `git commit`
is invoked.
Prompt: Commit the previously approved message.
Pass: The skill discards the stale draft, recollects staged evidence, and runs
the same gate for the new tree and message. Attended approval is requested
again; recorded preauthorization is re-evaluated.

## Scenario 5: Edge case — commit failure or interruption

Setup: `git commit -F` fails, or the process is interrupted after the temporary
message file is created.
Prompt: Commit and report the result.
Pass: Cleanup removes the message file. A failure reports the command, status,
and Git error without reporting a SHA or subject as if a commit succeeded.
