---
name: integration-branch-orchestrator
description: Use when planning or supervising a long-running autonomous GitHub PR workflow with integration branches, blanket approval scope, multiple PRs, or human promotion gates.
tools:
  - bash
  - view
  - edit
  - grep
  - glob
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
- Fetch and record the current remote default/protected branch SHA before
  creating or verifying an integration branch.
- Use or create `integration/<feature-name>` from the identified
  default/protected branch as the autonomous landing branch.
- For an existing integration branch, verify ancestry from the identified
  default/protected branch before retargeting PRs or delegating closeout work.
- For an existing integration branch, verify current branch commits and diff are
  in scope for this run. If they are not, recreate it from the protected base or
  block for human topology approval before delegation.
- Ensure the integration branch exists on the remote before retargeting existing
  PRs or creating new PRs against it.
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

1. Define the branch topology.
   - Identify source branches or PRs.
   - Fetch the remote default/protected branch and record the current ref/SHA.
   - Create `integration/<feature-name>` from the default/protected branch ref,
     or verify an existing integration branch has that ancestry.
   - For an existing integration branch, fetch its current remote ref before
     verifying ancestry or scope; do not evaluate ancestry or in-scope commits
     against a stale local copy.
   - For an existing integration branch, verify its current commits and diff are
     in scope for this run, or recreate it from the protected branch before
     delegation only when destructive integration-branch recreation is
     explicitly authorized and no open PR targets the existing integration
     branch (PRs target the branch by name, not a specific tip SHA, so any
     open PR based on it is invalidated by a reset); otherwise block for
     human topology approval.
   - Push the integration branch or verify the remote branch exists before
     retargeting or creating integration-targeted PRs.
   - For each existing PR, verify its base branch is `integration/<feature-name>`
     before closeout delegation.
   - If an existing PR targets the default branch, retarget it to the integration
     branch or create a new integration-targeted PR before delegating only when
     PR topology edits are authorized.
   - Prefer retargeting an existing PR over cloning it. If a new
     integration-targeted PR is created from an existing PR, import and triage
     the original PR's unresolved review feedback, review-level feedback, and PR
     conversation comments before delegation.
   - If the original PR stays open after cloning, close or supersede it only
     when that action is explicitly authorized; otherwise keep polling it for
     new reviews, conversation comments, and unresolved threads until the
     integration-targeted PR merges. A one-time feedback import does not
     cover activity added to the original PR afterward.
   - If a source branch has no PR, verify the source branch exists on a
     recorded remote, pushing it first when authorized, then create an
     integration-targeted PR only when PR topology edits are authorized, or
     block until the user explicitly defines separate branch-only gates.

2. Define gates.
   - Approval must be fresh for each PR's current head SHA and PR body.
   - Approval must also cover each PR's current target/base branch.
   - Required remote checks must be green for each current head before merge.
   - Local tests must pass before each merge into integration.
   - No unresolved actionable review feedback may remain.
   - No unrelated local/user changes may be staged, committed, overwritten, or
     hidden.

3. Dispatch closeout work.
   - For each concrete PR whose base is `integration/<feature-name>`, invoke
     `pr-closeout-loop` with target branch set to `integration/<feature-name>`.
   - Dispatch PRs with failing, pending, or stale required checks so the closeout
     loop can fix or wait on CI; do not merge them until checks are green.
   - Keep each loop scoped to its own PR.
   - Run concurrent closeout loops in separate worktrees or clones. If only one
     checkout is available, serialize the loops so branch, index, validation,
     commit, and push state cannot overlap.
   - If a loop finds conflicting feedback, stale authorization, or missing
     validation, mark that item blocked instead of widening scope.

4. Maintain the integration branch.
   - `pr-closeout-loop` owns each PR's merge into `integration/<feature-name>`
     and must apply its full merge-gate set (fresh approval, green checks
     against the current base, passing local suite, no actionable feedback,
     final pre-merge refresh) immediately before merging. Do not perform an
     independent merge here that bypasses those gates.
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
