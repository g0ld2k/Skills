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

## Replies and Resolution

Use `pr-comment-review`'s canonical reply preview and approved digest. Its
complete inventory and fresh per-thread target checks own reply posting.

Before resolving, freeze the repository and PR, thread/root IDs, complete
thread digest, required reply or acknowledgement ID, resolution policy, and
authorization. Immediately re-fetch the full thread and target. Require the
same digest, unresolved state, required acknowledgement, policy eligibility,
and exact authorization. New comments or changed state return to triage. After
resolution, verify that exact thread is resolved. Re-fetch the closeout
snapshot after either mutation; never reuse the prior G4 result.

## Merge

Freeze the PR, closeout-surface digest, complete feedback digest, gate evidence,
target, method, authorization, and expected head OID. Re-fetch every input and
evaluate G1–G7 together immediately before the merge request. Use a merge
operation conditioned on the expected head OID, such as GitHub's REST merge
`sha` parameter. If the available client cannot enforce the condition, block;
a separate refresh cannot close that race.

After the request, fetch terminal PR state and the merge commit. Report success
only when the expected PR is merged by the approved method into the approved
target. A closed-but-unmerged PR, unexpected head/base transition, or ambiguous
result is a blocker, not success.
