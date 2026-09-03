# Closeout Safety

Read this reference after selecting a mutation lifecycle and immediately before
its first local or remote mutation.

## Exact-Head Checkout

Record the live PR head repository, ref, and OID before touching the checkout.
Preserve the initial worktree/index inventory. Inspect or fix that OID in an
isolated checkout when alignment would overwrite, hide, stage, or mix unrelated
work. A head change discards the disposition and returns to inventory.

## Commit and Push

Freeze one push plan:

| Field | Required value |
| --- | --- |
| Commit | exact approved local OID |
| Target | effective remote URL and full `refs/heads/...` ref |
| Transition | observed remote `before_oid` → approved commit OID |
| Scope | files committed plus authorization for commit and push |
| Evidence | validation tied to the commit and current base OID |

Immediately before pushing, fetch or read the remote ref and require
`before_oid`. Verify that OID is an ancestor of the approved commit, forbidding
a history rewrite. Then make the update an atomic compare-and-swap with an
exact-ref lease while pushing the approved OID, never live `HEAD`:

```text
git push \
  --force-with-lease=refs/heads/<approved_ref>:<before_oid> \
  <effective_remote_url> \
  <approved_oid>:refs/heads/<approved_ref>
```

The lease is only the compare-and-swap guard; the ancestry check still permits
only a normal fast-forward update. A lease failure, different URL/ref, or
changed before-OID discards the plan without pushing. After success, re-fetch
the PR and remote ref. Accept only the recorded before→approved transition;
concurrent head, base, body, or PR-state drift returns to inventory and renews
stale evidence or approval.

## Acknowledgements and Resolution

Use `pr-comment-review`'s canonical reply preview and approved digest. Its
complete inventory and fresh per-thread target checks own reply posting.

For PR-conversation or review-level feedback, freeze repository/PR, feedback ID
and digest, exact acknowledgement bytes/digest, channel, before-state, intended
after-state, and authorization. Immediately before posting, re-fetch that
surface and require an exact match; drift returns to triage. Verify the posted
bytes and identity, then refresh closeout state.

Thread resolution requires a mutation that atomically conditions on the frozen
complete-thread digest or version. If the platform lacks that condition, keep
the thread unresolved. A replied unresolved thread is G4-clear only when the
latest complete inventory shows no actionable final-state content; later
replies remain visible and return to triage. When an atomic condition exists,
freeze repository/PR, thread/root IDs, digest/version, acknowledgement,
resolution policy, and authorization; verify resolution afterward. Never reuse
the prior G4 result after any mutation.

## Merge

Freeze the PR URL/target repository, closeout and feedback digests, gate
evidence, target ref/base OID, explicit method, authorization, and head OID.
Re-fetch every input and evaluate G1–G7 together immediately before requesting
merge. The operation must bind the recorded repository and method and
atomically reject either head or base-surface drift. GitHub CLI
`--match-head-commit` and the REST `sha` parameter constrain only head; when no
available operation also enforces base ref/OID, block automated merge and name
the exact manual or queue action required. A separate refresh cannot close the
race.

After the request, fetch terminal PR state and the merge commit. Report success
only when the expected PR is merged by the approved method into the approved
target. A closed-but-unmerged PR, unexpected head/base transition, or ambiguous
result is a blocker. Confirmed merge-queue enrollment is progress, not success:
return to monitoring until terminal state or wait exhaustion. Queue enrollment
must be separately authorized for a base that can advance. Without that scope,
require an available cancellation/dequeue operation and invoke it immediately
when the frozen base changes; if cancellation cannot be guaranteed, do not
enroll automatically. After cancellation, discard G1–G3 and rebuild them on
the new base before any re-enrollment.
