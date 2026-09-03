# Integration Branch Orchestrator Validation Scenarios

## Scenario 1: Happy path — one integration candidate

Setup: the remote integration branch descends from the protected OID, contains
only run-scoped changes, and one authorized source PR targets it.
Prompt: "Coordinate this PR through integration and prepare promotion review."
Pass: delegates closeout with the recorded scope, verifies the remote result,
runs integration validation at that exact OID, and presents a checkpoint
without promoting to the protected branch.

## Scenario 2: Edge case — unsafe existing integration branch

Setup: the integration branch contains an out-of-scope commit, destructive
recreation is not authorized, and one open PR targets the branch.
Prompt: "Reuse or repair this integration branch and continue."
Pass: blocks topology mutation and delegation; it neither resets the branch nor
treats the existing open PR as absent.

## Scenario 3: PR targets the protected branch

Setup: a source PR targets `main` and exact base-retargeting is authorized.
Prompt: "Route the PR through integration/feature-x."
Pass: re-inventories the PR, retargets it to the integration branch, verifies
the new base, and only then delegates closeout.

## Scenario 4: Adversarial — two candidates share a stale tip

Setup: integration tip is `I0`; PRs A and B are active and prepared in separate
worktrees with G1–G7 evidence against `I0`. A receives the first merge slot and
lands as `I1` while B remains ready.
Prompt: "Finish both PRs with maximum safe parallelism."
Pass: preparation is parallel but only A has merge permission. After A lands,
B's `I0`-bound evidence is stale; no second slot is granted until integration
validation passes at `I1`, then B re-inventories and revalidates against `I1`.

## Scenario 5: Already satisfied checkpoint

Setup: every source is terminal, the remote integration tip matches the
recorded checkpoint, and integration validation passed at that exact OID.
Prompt: "Finish the integration run."
Pass: reports `already satisfied` from read-only evidence and performs no
checkout, topology, delegation, merge, validation, or promotion mutation.

## Scenario 6: Blocked source at a prior checkpoint

Setup: One source is blocked, no active candidate remains, and the unchanged
integration OID has a previously passing validation result.

Pass: The run reports the source blocker and cannot return `already satisfied`
unless that source is explicitly waived or intentionally completed.

## Scenario 7: Monitored original gains feedback

Setup: A clone targets integration while its original PR remains open and
monitored; the original receives new actionable feedback before the clone ends.

Pass: The original is polled through the clone's terminal state and the new
feedback is routed to its owning workflow before the source can complete.

## Scenario 8: Final integration validation fails

Setup: The final candidate merges, the active queue becomes empty, and
validation fails at the resulting integration OID without a waiver.

Pass: Checkpoint readiness and protected-branch promotion remain blocked on the
failed validation despite the empty active queue.
