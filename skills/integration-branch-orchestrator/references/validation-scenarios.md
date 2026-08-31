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

## Scenario 4: Deterministic — two-PR stale-tip race

Setup: `integration/feature-x` is at remote tip `I0`; PRs A and B are both
active, target the branch, and have passed G1–G7 against `I0`. Separate
worktrees are available, normal merge commits are required, and one
integration-wide coordinator is available. At slot admission, A is ready and
selected for the first slot so the tip transition is deterministic; candidate
selection remains readiness-based rather than source-ordered.
Prompt: "Run parallel closeout preparation for A and B, then serialize their
integration merges with the coordinator and validate after each merge."
Pass:

1. Delegates both loops with merge authorization excluded.
2. The coordinator grants A a slot and records `slot_base_sha=I0`. Immediately
   before merging, A fetches the integration tip and live PR state, confirms
   the tip is still `I0`, performs `pr-closeout-loop`'s final G1–G7 evaluation
   against `I0`, and merges normally, producing `I1`.
3. Fetches and records `I1`, then passes integration validation before another
   slot is granted.
4. The coordinator marks B's earlier `I0` evidence stale, grants B the next
   slot, and records `slot_base_sha=I1`. B refreshes and revalidates against
   `I1`; immediately before merging, B fetches the tip and live PR state,
   confirms the tip is still `I1`, passes the final G1–G7 evaluation, and
   merges normally, producing `I2`.
5. Fetches and records `I2` and passes integration validation before reporting
   promotion readiness.

The ledger proves that A and B never both pass the final merge gate against the
same stale tip `I0`, and records both post-merge validation results.
