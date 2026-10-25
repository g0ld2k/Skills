# GitHub Repo Setup Validation Scenarios

`tests/test_github_repo_setup.py` covers the script against a stub `gh`. These
scenarios cover the agent's ordering and authority. Mock every `gh` write; never
point an evaluation at a real repository.

## Scenario 1: Fresh repository

Setup: a repository with merge commits allowed, no ruleset, no workflows, and an
Xcode Cloud check on its latest PR.
Prompt: "$github-repo-setup for OWNER/NAME."
Pass: reads the CI check name and app id from check runs; shows the settings dry
run before applying; opens the workflows PR; runs the ruleset phase only after
that PR has merged; finishes with `verify` all `ok`.

## Scenario 2: Third-party action in an existing workflow

Setup: an existing workflow uses `some-org/setup-thing@v2`.
Pass: flags it before applying settings and puts a replacement (a `run` step or
a pinned GitHub-owned action) in the workflows PR.

## Scenario 3: Ruleset requested before the workflows merge

Prompt: "Just add the required checks now."
Pass: the ruleset phase refuses because the workflow files are not on the
default branch, and the agent explains that the checks would block every PR.

## Scenario 4: Not invoked implicitly

Prompt: "Why can't I merge this PR?"
Pass: the skill does not activate.
