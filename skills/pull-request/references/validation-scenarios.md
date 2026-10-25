# Pull Request Validation Scenarios

## Scenario 1: Logic change

Setup: a fixture branch that changes a cache check, with a passing unit test.
Prompt: "Write the PR for this branch."
Pass: the title is a Conventional Commit subject; the body opens with one or two
plain sentences, then Summary (a diff-sketch or pseudocode, not a file list),
Evidence citing the test actually run, and Merge Danger with Door and Blast Radius.

## Scenario 2: UI change

Setup: a fixture repo whose `AGENTS.md` names a launch command, with a branch that
changes a screen.
Prompt: "Open a PR for this."
Pass: captures "before" from the base branch built in a temporary worktree and
"after" from the branch, with the same device and data; references both as
`![alt](./file.png)` and passes the same paths to `--attach`; commits no images.
Mock `gh pr create`; do not publish.

## Scenario 3: One-way door

Setup: a branch that changes a persisted schema or deletes user data.
Prompt: "Write the PR body."
Pass: Door is one-way with the reason, and the PR gets the
`needs-human-verification` label.

## Scenario 4: Adjacent request

Prompt: "Reply to the review comments on this PR."
Pass: the skill does not activate; review replies belong to `pr-comment-review`.
