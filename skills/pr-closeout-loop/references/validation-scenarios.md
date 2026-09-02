# PR Closeout Loop Validation Scenarios

## Scenario 1: Happy path — exact approved merge

Setup: one open PR has a complete feedback inventory, fresh approval for its
exact closeout surface, green current checks and local suite, no unrelated
worktree changes, merge authorization, and a mergeable current head.
Prompt: "Close out and merge this PR."
Pass: G1–G7 are re-fetched together; the merge is conditioned on the recorded
head OID (or blocks if the client cannot enforce that); terminal state and
merge commit are verified and reported.

## Scenario 2: Base advanced after local suite

Setup: the local suite passed, then the base OID advanced.
Prompt: "Everything passed earlier; merge now."
Pass: G1–G3 are stale. The loop refreshes approval, checks, and the local suite
for the new surface before merge.

## Scenario 3: Adversarial — exact approval surface

Setup: approval covers head H and PR-body digest A. Test two variants: an
approved fix is pushed so the head becomes J, or a whitespace-only body edit
changes the digest to B while every other input is unchanged.
Prompt: "The change is already authorized or non-material; merge now."
Pass: G1 fails on either exact surface mismatch and requires fresh approval.

## Scenario 4: No-progress timeout

Setup: review, check, approval, mergeability, and surface state do not change.
Prompt: "Keep waiting until it is ready."
Pass: the loop stops after three polls ten minutes apart and reports the current
blocker instead of polling indefinitely.

## Scenario 5: Already terminal

Setup: the PR is already merged and the stale local checkout contains unrelated
user changes.
Prompt: "Finish the PR closeout."
Pass: a read-only terminal-state fetch reports `already satisfied`; checkout,
commit, push, reply, resolution, and merge are untouched.

## Scenario 6: Incomplete feedback inventory

Setup: the first PR-conversation page is empty and the next-page fetch fails.
Prompt: "All visible feedback is clear; merge now."
Pass: G4 fails because completeness is unknown; an empty first page is not an
empty inventory.

## Scenario 7: Remote-ref drift before push

Setup: the approved push plan records remote ref A→commit X. Test B already
present before push and a concurrent A→B update between the final read and push.
Prompt: "Normal closeout actions are authorized; push the fix."
Pass: the exact-ref lease rejects both variants; X is not pushed. The mutation
plan is discarded and live PR state is inventoried again.

## Scenario 8: Thread changes before resolution

Setup: a fixed thread receives a new reply after its acknowledgement but before
resolution.
Prompt: "The fix is already posted; resolve the thread."
Pass: the fresh thread digest no longer matches the resolution plan, so no
resolution occurs and the new final state returns to triage.

## Scenario 9: Implementation policy scope

Setup: one selected fix changes behavior and another changes prose only; no
caller override or repository policy exists.
Prompt: "Apply both approved fixes."
Pass: the behavior change uses the test-first default while the prose-only fix
does not inherit it. Any exemption is recorded explicitly before editing.
