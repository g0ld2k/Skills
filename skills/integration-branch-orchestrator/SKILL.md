---
name: integration-branch-orchestrator
description: Control-plane supervision for multi-PR closeout through an integration branch and human promotion gate.
license: MIT
disable-model-invocation: true
---

# Integration Branch Orchestrator

## Goal

Plan and supervise autonomous PR closeout work without letting unattended changes
flow directly into the default branch. Establish an integration branch boundary,
define approval scope, hand concrete PRs to `pr-closeout-loop`, and preserve a
human checkpoint before protected/default branch promotion.

This is the control-plane skill. If a concrete PR already has a target branch
and only needs review/CI closeout, use `pr-closeout-loop` directly.

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
  before delegating to `pr-closeout-loop`.
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
   `pr-closeout-loop`).

   - T1. List source branches/PRs in scope.
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
   - T5. For each source branch without a PR: verify the branch exists on a
     recorded remote (push first if authorized), then create an
     integration-targeted PR (requires PR-topology authorization); otherwise
     Block until the user defines branch-only gates.
   - T6. Verify every delegatable item now has a PR whose base is
     `integration/<feature-name>`.
   - T7. Record in the run notes: integration branch SHA, items in scope,
     authorizations in effect.

2. Define gates.
   - Each PR's merge is gated by `pr-closeout-loop`'s G1–G7; the orchestrator
     does not evaluate per-PR gates or merge PRs itself.
   - Integration validation must pass after merges into the integration branch.
   - No unrelated local/user changes may be staged, committed, overwritten, or
     hidden.

3. Dispatch closeout work.
   - For each concrete PR whose base is `integration/<feature-name>`, invoke
     `pr-closeout-loop` with target branch set to `integration/<feature-name>`.
   - Dispatch PRs with failing, pending, or stale required checks so the closeout
     loop can fix or wait on CI.
   - Keep each loop scoped to its own PR.
   - Run concurrent closeout loops in separate worktrees or clones. If only one
     checkout is available, serialize the loops so branch, index, validation,
     commit, and push state cannot overlap.
   - If a loop finds conflicting feedback, stale authorization, or missing
     validation, mark that item blocked instead of widening scope.

4. Maintain the integration branch.
   - `pr-closeout-loop` owns each PR's merge into `integration/<feature-name>`
     and must apply its full G1–G7 merge-gate set immediately before merging.
     Do not perform an independent merge here that bypasses those gates.
   - Once a delegated merge has landed, use normal merge commits by default.
   - Fetch and check out the current remote `integration/<feature-name>` tip
     before running integration-level validation. Delegated merges made
     through GitHub or in separate worktrees/clones may not be reflected in
     the orchestrator's own checkout, so validating a stale local copy can
     report the branch ready for promotion when the merged result actually
     fails.
   - Re-run integration-level validation after merges when the repository has a
     suitable suite or workflow.
   - If integration validation fails, triage whether the failure belongs to a
     just-merged branch, branch interaction, or environment, but keep promotion
     blocked until validation passes or the failure is explicitly waived.

5. Prepare human checkpoint.
   - Summarize branches/PRs included, commits merged, review feedback resolved,
     validation run, CI state, deferred low findings, and known risks.
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
- integration validation fails and has not been explicitly waived;
- promotion would touch the protected/default branch without explicit approval;
- unrelated local/user changes would be affected.

## Output

Report:
- integration branch name;
- PRs or branches in scope;
- unattended actions authorized;
- items completed, blocked, or waiting;
- validation and CI state;
- whether the integration branch is ready for human review or promotion.

## References

- references/conventions.md for capability ladder, temp files, external-text, and Blocked Report conventions.
