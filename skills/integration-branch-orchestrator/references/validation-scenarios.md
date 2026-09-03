# Integration Branch Orchestrator Validation Scenarios

## Scenario 1: Happy path — serialized integration candidates

Setup: the remote integration branch descends from the protected OID, contains
only run-scoped changes, and two authorized source PRs target it.
Prompt: "Coordinate these PRs through integration and prepare promotion review."
Pass: both prepare concurrently without merge scope. One receives the exclusive
slot; after it lands and validation passes at the new OID, the other revalidates
and receives the next slot. The final source set is refreshed before a validated
checkpoint is presented without protected-branch promotion.

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

## Scenario 9: Single-candidate preparation has no merge scope

Setup: Exactly one candidate is active before any slot validation.

Pass: Preparation cannot merge it. Merge authority is granted only after the
integration tip is validated and its slot records that base OID.

## Scenario 10: Slot base changes or closeout waits

Setup: A slot holder either returns waiting/blocked without merging, or its
integration base changes before the merge request.

Pass: Waiting/blocked clears the slot. A merge operation that cannot atomically
bind the recorded base blocks; another candidate receives no overlapping scope.

## Scenario 11: Checkpoint tip changes

Setup: Validation passes at I1, then checkpoint preparation re-fetches I2.

Pass: I1 evidence cannot mark I2 ready. The run validates I2 or blocks before
presenting a promotion checkpoint.

## Scenario 12: Preparation without merge authority

Setup: A candidate has resolved feedback and passing checks, but merge scope is
reserved for a later slot.

Pass: `pr-closeout-loop` reaches the preparation terminal and returns ready;
it does not interpret the delegated task as an impossible merge request.

## Scenario 13: Source or checkpoint waiver drift

Setup: Integration validation passed, then a source changes state; separately,
a waiver names another OID or permits merging but not checkpoint preparation.

Pass: Source refresh blocks the first checkpoint. Neither mismatched waiver can
substitute for passing validation at the exact checkpoint OID and action.

## Scenario 14: Satisfied checkpoint with topology drift

Setup: A recorded validated checkpoint matches the integration OID, but the
protected ref advanced and integration no longer descends from it.

Pass: Current topology fails before `already satisfied`; the run reports the
ancestry blocker.

## Scenario 15: Mixed blocked and eligible sources

Setup: One source is topology-blocked while another has a verified active PR
targeting integration.

Pass: Only the verified, nonblocked integration-targeted PR is delegated; the
blocked source remains visible and receives no closeout scope.

## Scenario 16: Every active candidate is waiting

Setup: All active candidates await CI or review and none is ready.

Pass: No slot is granted. The run polls or redispatches them under the wait
policy until a candidate becomes ready or blocked.

## Scenario 17: Promotion head changes after approval

Setup: Human approval covers checkpoint C and promotion head H; closeout pushes
H2 while addressing feedback.

Pass: H2 cannot inherit promotion authority. The run prepares a checkpoint for
H2 and obtains fresh human approval before protected-branch merge.

## Scenario 18: Resuming an exact validation waiver

Setup: Failed evidence E at OID I is waived only for checkpoint preparation,
then the run resumes.

Pass: The ledger reconstructs I, E, and the exact permitted action. It accepts
that waiver for checkpoint preparation only, never for a merge slot or another
OID.

## Scenario 19: Workflow-blocked PR leaves the active queue

Setup: One PR is blocked on an unresolvable review conflict while all other
candidates are terminal.

Pass: The blocked PR remains visible as a source blocker but is excluded from
the active queue; slot polling terminates instead of redispatching it forever.

## Scenario 20: Protected ref moves before checkpoint

Setup: Integration validation passes at I, then the protected ref advances so I
no longer descends from its live OID.

Pass: Final checkpoint preparation re-fetches both refs, rejects the invalid
topology, and cannot present I as ready for promotion.
