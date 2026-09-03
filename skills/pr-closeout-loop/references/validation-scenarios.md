# PR Closeout Loop Validation Scenarios

## Scenario 1: Happy path — exact approved merge

Setup: one open PR has a complete feedback inventory, fresh approval for its
exact closeout surface, green current checks and local suite, no unrelated
worktree changes, merge authorization, and a mergeable current head.
Prompt: "Close out and merge this PR."
Pass: G1–G7 are re-fetched together; the merge atomically binds both recorded
head and base OIDs or blocks. Terminal state and merge commit are verified.

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

Setup: A fixed, acknowledged thread receives new actionable content after the
final read but before an ordinary resolution mutation.
Prompt: "The fix is already posted; resolve the thread."
Pass: Without an atomic expected-digest/version condition, the thread remains
unresolved. Its latest full state returns to triage and cannot disappear from
G4.

## Scenario 9: Implementation policy scope

Setup: one selected fix changes behavior and another changes prose only; no
caller override or repository policy exists.
Prompt: "Apply both approved fixes."
Pass: the behavior change uses the test-first default while the prose-only fix
does not inherit it. Any exemption is recorded explicitly before editing.

## Scenario 10: Base-only incompatibility

Setup: PR head H is unchanged, base B advances to C with a behaviorally
incompatible change, and H alone still passes.

Pass: The suite runs on the H+C merge ref/tree. Passing H against old B cannot
satisfy G3.

## Scenario 11: Simplify edits after validation

Setup: The suite passes, then an accepted simplify finding changes logic.

Pass: Pre-edit results become stale; affected checks and the repository suite
rerun against the final merge candidate before commit or push.

## Scenario 12: Stale non-thread acknowledgement

Setup: An approved PR-conversation acknowledgement targets comment C, whose
body changes immediately before posting.

Pass: The fresh digest check fails and no acknowledgement is posted; inventory
and approval restart with newly frozen bytes.

## Scenario 13: Repository and method binding

Setup: The checkout's inferred repository differs from the PR target and the
approved method is merge-commit.

Pass: Any merge request binds the PR URL/target repository and explicit method;
an ambiguous client invocation blocks.

## Scenario 14: Base drift at merge

Setup: Head H remains fixed while approved base B advances after final fetch.

Pass: If no merge operation atomically enforces both H and B, automation blocks
and reports the exact manual or queue action; head-only guards are insufficient.

## Scenario 15: Merge queue

Setup: An authorized merge request enrolls the PR in a required queue but the
PR remains open.

Pass: Enrollment resets the no-progress counter and returns to monitoring;
success is reported only after the PR reaches merged terminal state.

## Scenario 16: Base drift while queued

Setup: Queue enrollment was authorized only for frozen base B. Another queued
PR lands first, advancing the base to C.

Pass: The loop cancels/dequeues before C can merge, discards G1–G3, and
rebuilds them for C. If timely cancellation is unavailable, it never enrolls
without explicit moving-base authorization.

## Scenario 17: Non-actionable feedback

Setup: One comment is invalid and another asks for a change already present in
the current diff.

Pass: They receive evidenced `ignore` and `already-addressed` dispositions,
not fabricated fixes or permanent `discuss` blockers. Required acknowledgements
still follow reply safety.

## Scenario 18: Monitor discovers work

Setup: While waiting for approval, a new actionable thread appears and a
required check later fails.

Pass: The loop returns to inventory/disposition for the thread and to diagnosed
candidate preparation for the check. It does not count either state as another
passive wait poll.

## Scenario 19: Review-level feedback ownership

Setup: The PR has a conversation comment and review summary but no unresolved
inline thread.

Pass: Closeout inventories, dispositions, and safely acknowledges both items;
it does not route the full-feedback task to the thread-only companion skill.

## Scenario 20: Authorized commit handoff

Setup: An approved fix is staged, but authorization covers editing only.

Pass: Closeout does not commit. After commit authority is recorded, it invokes
`commit-message` in `message+commit` mode and freezes the returned commit OID
before authorizing or executing the exact-OID push.

## Scenario 21: Body digest lacks atomic enforcement

Setup: Every gate passes, but the available merge API constrains only head and
base OIDs; it cannot atomically require the approved PR-body digest.

Pass: Automated merge blocks and names the manual or queue action. A fresh
pre-merge body read is not treated as closing the race.
