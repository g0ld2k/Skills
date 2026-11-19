# Pull Request Validation Scenarios

## Scenario 1: Logic change

Setup: a fixture branch that changes a cache check, with a passing unit test.
Prompt: "Write the PR for this branch."
Pass: the title is a Conventional Commit subject; the body opens with one or two
plain sentences, then Summary (a diff-sketch or pseudocode, not a file list),
Evidence citing the test actually run, and Merge Danger with Door and Blast Radius.

## Scenario 2: UI change

Setup: a fixture repo whose `AGENTS.md` names a launch command. The branch moves
Save into a compact toolbar. The supplied design shows its position and size.
Prompt: "Open a PR for this."
Pass: capture the base in a temporary worktree and the branch on the same device
with the same data. Inspect Save at toolbar size against the design. Tap it after
editing an item, reopen the item, and report which value appears. If input
is unavailable, report the visual comparison and identify the unverified action.
Reference both images as `![alt](./file.png)`, pass matching paths to `--attach`,
and keep them out of the commit. Mock `gh pr create` for this scenario.

## Scenario 3: One-way door

Setup: a branch that changes a persisted schema or deletes user data.
Prompt: "Write the PR body."
Pass: Door is one-way with the reason, and the PR gets the
`needs-human-verification` label.

## Scenario 4: Adjacent request

Prompt: "Reply to the review comments on this PR."
Pass: the skill does not activate; review replies belong to `pr-comment-review`.
