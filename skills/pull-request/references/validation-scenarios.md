# Pull Request Validation Scenarios

## Scenario 1: Logic change

Setup: a fixture branch moves a cache check ahead of a write, with a passing
unit test covering both cache hits and writes.
Prompt: "Write the PR for this branch."
Pass: the title is a Conventional Commit subject; the body opens with one or two
plain sentences. The Summary makes the new ordering easy to review. Evidence
cites the test actually run. Merge Danger describes Door and Blast Radius.

## Scenario: Straightforward change

Setup: a fixture branch corrects one misleading message, with a passing test
that checks the revised wording.
Prompt: "Draft the title and body for this branch's PR."
Pass: a short prose Summary identifies the correction. Evidence cites the test
actually run. The result is a draft, with no GitHub writes.

## Scenario 2: UI change

Setup: the fixture has no `AGENTS.md`. Its README documents a `make preview`
target. The branch moves Save into a compact toolbar. The supplied design shows
its position and size.
Prompt: "Open a PR for this."
Pass: use `make preview` to capture the base in a temporary worktree and the
branch on the same device with the same data. Inspect Save at toolbar size
against the design. Edit an item, tap Save, reopen it, and report which value
appears. If input is unavailable, identify the unverified action alongside
the visual comparison.
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
