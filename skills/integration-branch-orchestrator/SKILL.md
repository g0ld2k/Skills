---
name: integration-branch-orchestrator
description: Use when supervising autonomous multi-PR closeout through an integration branch with a human promotion gate.
license: MIT
compatibility: >-
  Requires a client/session authoritative skill catalog; delegated closeout
  may require superpowers:brainstorming, superpowers:writing-plans,
  superpowers:test-driven-development, and superpowers:systematic-debugging.
---

# Integration Branch Orchestrator

## Prerequisite Gate

Run this gate as step 0, before any task-related repository, filesystem, Git,
network, PR, CI, or branch-state read or mutation. The client/session's
authoritative skill catalog is the only availability source; do not infer
availability from files, manifests, prior turns, or a partial invocation.

Read the complete client/session catalog with exact qualified names once and
cache that snapshot for the run. Record `catalog_source`, `required`,
`present`, and `missing`. This plugin's bundled catalog identities are
`g0ld2k-skills:pr-generator`,
`g0ld2k-skills:pr-closeout-loop`, `g0ld2k-skills:pr-comment-review`,
`g0ld2k-skills:simplify`, and `g0ld2k-skills:commit-message`; use the catalog
spelling verbatim.

| Active branch | Required qualified catalog names |
| --- | --- |
| Topology read or integration validation only | — |
| Integration-targeted PR creation | `g0ld2k-skills:pr-generator` |
| Delegated reply-only closeout | `g0ld2k-skills:pr-closeout-loop`, `g0ld2k-skills:pr-comment-review` |
| Delegated in-scope code fix | Add `superpowers:test-driven-development` |
| Delegated ambiguous or multi-step fix | Add `superpowers:brainstorming`, `superpowers:writing-plans` |
| Delegated failing-check diagnosis | Add `superpowers:systematic-debugging` |
| Delegated non-trivial fix before commit | Add `g0ld2k-skills:simplify`, `g0ld2k-skills:commit-message` |

Rows beginning with "Add" are cumulative with the delegated closeout row and
each other active row. At step 0, take the union of every row foreseeably
activated by the requested and authorized lifecycle, including the transitive
closure for delegated `g0ld2k-skills:pr-closeout-loop` work. Reuse the cached
catalog snapshot and derived closure; do not rescan it for each candidate or
helper. If later topology or PR evidence activates a conditional row that was
not knowable at entry, extend the closure against the snapshot before its first
side effect. Refresh only if the client reports that the catalog changed. A
validation-only or no-change path never requires implementation-only names.
Never stop at the first missing name, substitute a similarly named skill, or
invoke a dependency to test whether it is present. Report all missing names in
the active closure together. A missing bundled name means the `g0ld2k-skills`
installation is broken or incomplete: stop with reinstall or upgrade guidance
for the root plugin and require a fresh catalog. A missing `superpowers:*` name
is an install prerequisite; name it exactly and wait for installation. If the
catalog cannot be exposed, emit:

    BLOCKED: P0 — authoritative skill catalog unavailable; prerequisites cannot be verified
    Last completed step: 0
    Would unblock: expose the complete client/session catalog with exact qualified names and provider/source

Do not read repository or branch state after this block. For missing entries,
emit one Blocked Report containing the full `missing` list and the
category-specific reinstall/install guidance.

## Goal

Plan and supervise autonomous PR closeout work without letting unattended changes
flow directly into the default branch. Establish an integration branch boundary,
define approval scope, hand concrete PRs to
`g0ld2k-skills:pr-closeout-loop`, and preserve a human checkpoint before
protected/default branch promotion.

This is the control-plane skill. If a concrete PR already has a target branch
and only needs review/CI closeout, use
`g0ld2k-skills:pr-closeout-loop` directly.

## Planning Inputs

Establish:
- feature or batch name for `integration/<feature-name>`;
- source branches or PRs in scope;
- default/protected branch name;
- current remote default/protected branch ref and SHA to use as the
  integration branch starting point;
- whether each source branch already has a PR, or needs an integration-targeted
  PR created before closeout;
- approval signal and freshness requirements for each PR;
- integration merge owner: one integration-wide coordinator or repository merge
  queue that can grant a single candidate a merge slot;
- allowed unattended actions: fixes, commits, pushes, replies, thread
  resolution, PR creation, PR base-retargeting, merges into integration,
  destructive integration-branch recreation (recreating or resetting an
  existing `integration/<feature-name>` from the protected base), closing or
  superseding a cloned PR's original PR;
- actions that still require human approval, especially integration-to-default
  promotion.

## Orchestration Policy

Default strategy:
- Require each closeout item to have a PR targeting the integration branch
  before delegating to `g0ld2k-skills:pr-closeout-loop`.
- Separate parallel review, fix, and CI preparation from serialized final merge
  slots on a shared integration branch.
- When more than one candidate is active, delegate with merge authorization
  explicitly excluded. A single integration-wide coordinator or repository
  merge queue grants one ready candidate a merge slot; selection may be based on
  readiness rather than source order.
- Keep slot discipline until every candidate from that multi-candidate run has
  finished; do not restore blanket merge authorization as the queue drains.
- Treat a repository merge queue as the merge owner only when it admits one
  candidate at a time and waits for required post-merge integration validation
  before admitting the next candidate.
- Preserve branch history with normal merge commits unless the user or repo
  requires another method.
- Let blanket approval cover repeated valid fixes, commits, pushes, replies,
  thread resolution, PR topology edits, and gated merges into the integration
  branch only when those action categories were explicitly authorized.
- Require explicit human approval before merging the integration branch into the
  protected/default branch.

Do not choose direct default-branch promotion silently. If the user wants that,
confirm the authorization scope and merge gates first.

## Workflow

1. Define the branch topology. Work through T1–T7 in order; each has an
   explicit on-failure action. "Block" always means: stop delegation for the
   affected item and emit a Blocked Report (shape defined in
   `g0ld2k-skills:pr-closeout-loop`).

   - T1. Complete the Prerequisite Gate for every branch already active from the
     request, then list source branches/PRs in scope.
   - T2. Fetch the remote default/protected branch; record its ref and SHA.
   - T3. Resolve the integration branch:
     - Missing → create `integration/<feature-name>` from the recorded SHA and
       push it, ONLY IF branch creation and pushing are within the authorized
       scope for this run; otherwise Block for topology approval.
     - Exists → fetch its current remote ref (never evaluate a stale local
       copy), then pass gates E1–E3:

       | Gate | Check | On failure |
       | --- | --- | --- |
       | E1 Ancestry | branch descends from the recorded protected ref | Block for human topology approval |
       | E2 Scope | every commit/diff on the branch belongs to this run | Recreate from the protected SHA ONLY IF destructive recreation is explicitly authorized AND no open PR targets the branch (a reset invalidates PRs based on it); otherwise Block |
       | E3 Remote | branch exists on the remote | Push it if pushing is authorized; otherwise Block |

   - T4. For each existing source PR: if its base is not the integration
     branch, retarget it if PR-topology edits are authorized; otherwise Block
     that item for topology approval. Prefer retargeting over cloning. If a clone is created anyway, import and triage
     the original PR's unresolved review threads, review-level feedback, and PR
     conversation comments first, and either close/supersede
     the original (only if authorized) or keep polling it for new activity
     until the clone merges.
   - T5. For each source branch without a PR: confirm the cached prerequisite
     closure includes `g0ld2k-skills:pr-generator` before creating one. Verify
     the branch exists on a recorded remote (push first if authorized), then create an
     integration-targeted PR (requires PR-topology authorization); otherwise
     Block until the user defines branch-only gates.
   - T6. Verify every delegatable item now has a PR whose base is
     `integration/<feature-name>`.
   - T7. Record in the run notes: integration branch SHA, items in scope,
     authorizations in effect.

2. Define gates.
   - Each PR's merge is gated by `g0ld2k-skills:pr-closeout-loop`'s G1–G7; the
     orchestrator does not evaluate per-PR gates or merge PRs itself.
   - For a shared integration branch with multiple active candidates, the slot
     holder's closeout loop applies its canonical Merge Gates and Approval
     Freshness rules against the exact integration tip recorded on slot entry.
     The merge owner grants or revokes the slot and records the result; it does
     not replace the loop's gate evaluation.
   - Integration validation must pass after every merge before another merge
     slot is granted or promotion readiness is declared.
   - No unrelated local/user changes may be staged, committed, overwritten, or
     hidden.

3. Dispatch closeout work.
   - For each concrete PR whose base is `integration/<feature-name>`, confirm
     the cached closure contains the transitive closeout set, then invoke
     `g0ld2k-skills:pr-closeout-loop` with target branch set to
     `integration/<feature-name>`.
   - When more than one candidate is active, exclude merge authorization from
     every delegated loop for the rest of that multi-candidate run. Keep review,
     fixes, and CI preparation concurrent in separate worktrees or clones.
     Treat pre-slot base-sensitive results as provisional, and defer expensive
     base-sensitive suites until slot entry when they add no diagnostic value.
   - Dispatch PRs with failing, pending, or stale required checks so the closeout
     loop can fix or wait on CI.
   - Keep each loop scoped to its own PR.
   - If only one checkout is available, serialize preparation so branch, index,
     validation, commit, and push state cannot overlap.
   - If a loop finds conflicting feedback, stale authorization, or missing
     validation, mark that item blocked instead of widening scope.

4. Maintain the integration branch.
   - When more than one candidate is active, the integration-wide coordinator
     or repository merge queue grants one ready candidate one merge slot. The
     grant temporarily authorizes only that candidate's closeout loop to consume
     the slot; any ready candidate may be selected. The recorded user scope must
     still satisfy G5 for the exact integration branch and merge method.
   - On slot entry, fetch the remote `integration/<feature-name>` ref and record
     its exact `slot_base_sha`.
   - Immediately before merging, fetch the remote ref and compare its tip with
     `slot_base_sha`. A changed tip revokes the slot and
     makes the candidate's base-sensitive evidence stale. Before granting any
     new slot, record the new tip, re-run E1–E3, and run integration validation
     from it; block on failure. Re-fetch before granting a slot and require the
     remote tip to equal the validated SHA, repeating this check for a newer tip.
     Then route the candidate through refresh and revalidation.
   - If the tip is unchanged, the delegated closeout loop re-fetches live PR
     state and performs its single mandatory final G1–G7 evaluation against
     `slot_base_sha`. After the fresh gates pass, it uses its recorded
     G5-authorized merge method. The orchestrator does not perform an independent
     merge that bypasses those gates.
   - After each delegated merge, fetch and record the new remote integration
     tip, then run integration-level validation from that fresh tip before
     granting another slot or declaring promotion readiness.
   - If integration validation fails, triage whether the failure belongs to a
     just-merged branch, branch interaction, or environment, and block later
     slots and promotion until it passes or a recorded user authorization
     explicitly permits proceeding after that integration-validation failure.
     Never widen a PR's scope.

5. Prepare human checkpoint.
   - Summarize branches/PRs included, commits merged, review feedback resolved,
     merge-slot owners and tip transitions, per-merge integration validation,
     CI state, deferred low findings, and known risks.
   - Do not merge the integration branch into the default branch until the user
     explicitly approves that promotion.

## Blocking Conditions

Block orchestration when:
- branch topology is ambiguous and a safe default is not obvious;
- blanket approval scope is unclear;
- existing integration branch contents are out of scope and destructive
  recreation is not explicitly authorized, or any open PR targets the
  existing integration branch;
- PR creation or base-retargeting is needed but not authorized;
- any PR lacks a PR surface that can be delegated to the closeout loop;
- more than one candidate is active and neither an integration-wide coordinator
  nor a repository merge queue can grant a merge slot; parallel preparation may
  continue, but final merges remain blocked;
- integration validation fails after a merge and has not been explicitly
  waived;
- promotion would touch the protected/default branch without explicit approval;
- unrelated local/user changes would be affected.

## Output

Keep the run ledger auditable. Record:
- catalog source and snapshot identity, plus the exact required, present, and
  missing qualified names in the active closure;
- protected/default ref and SHA, integration branch, and topology tip SHA;
- every candidate, source ref, PR base, worktree, and delegation status;
- merge owner (coordinator or queue), slot candidate, `slot_base_sha`, fresh
  G1–G7/base-sensitive results, pre-merge tip, merge SHA, post-merge tip, and
  validation result for each slot;
- authorization scope, CI state, deferred low findings, risks, and promotion
  status.

Report:
- integration branch name;
- PRs or branches in scope;
- unattended actions authorized;
- items completed, blocked, or waiting;
- validation and CI state;
- whether the integration branch is ready for human review or promotion.

## References

- references/conventions.md for capability ladder, temp files, external-text, and Blocked Report conventions.
