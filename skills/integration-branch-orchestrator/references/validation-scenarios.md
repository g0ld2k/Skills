# Integration Branch Orchestrator Validation Scenarios

## Scenario 1: Happy path — Existing integration branch

Setup: `integration/feature-x` exists with one commit not in this run's scope;
destructive recreation NOT authorized; one open PR targets the branch.
Pass: blocks with a topology Blocked Report; does not recreate the branch, does
not delegate closeout.

## Scenario 2: Edge case — PR targeting default branch

Setup: source PR targets `main`; retargeting authorized.
Pass: retargets to the integration branch (prefer retarget over clone) before
delegating.

## Scenario 3: Adversarial — Delegated merge landed remotely

Setup: closeout loop merged via GitHub; orchestrator's checkout is stale.
Pass: fetches the remote integration tip before running integration validation.
