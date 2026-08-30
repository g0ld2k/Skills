# Integration Branch Orchestrator Validation Scenarios

## Scenario 1: Happy path — Existing in-scope integration branch

Setup: `integration/feature-x` exists on the remote from the recorded protected
base, its current commits are in this run's scope, one source PR targets it, and
branch creation, PR closeout delegation, and integration merges are authorized.
Prompt: "Use `integration-branch-orchestrator` to prepare the branch and
delegate closeout for the PR."
Pass: verifies ancestry, scope, and the remote tip; delegates the integration-
targeted PR to `pr-closeout-loop`, then runs integration validation after the
delegated merge without promoting to the protected default branch.

## Scenario 2: Edge case — PR targeting default branch

Setup: source PR targets `main`; retargeting authorized.
Prompt: "Use `integration-branch-orchestrator` to route the PR to integration/feature-x."
Pass: retargets to the integration branch (prefer retarget over clone) before
delegating.

## Scenario 3: Adversarial — Delegated merge landed remotely

Setup: closeout loop merged via GitHub; orchestrator's checkout is stale.
Prompt: "Use `integration-branch-orchestrator` to validate the merged integration branch."
Pass: fetches the remote integration tip before running integration validation.
