---
name: integration-branch-orchestrator
description: Use when planning or supervising a long-running autonomous GitHub PR workflow with integration branches, blanket approval scope, multiple PRs, or human promotion gates.
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
- whether each source branch already has a PR, or needs an integration-targeted
  PR created before closeout;
- approval signal and freshness requirements for each PR;
- allowed unattended actions: fixes, commits, pushes, replies, thread
  resolution, merges into integration;
- actions that still require human approval, especially integration-to-default
  promotion.

## Orchestration Policy

Default strategy:
- Use or create `integration/<feature-name>` as the autonomous landing branch.
- Require each closeout item to have a PR targeting the integration branch
  before delegating to `pr-closeout-loop`.
- Preserve branch history with normal merge commits unless the user or repo
  requires another method.
- Let blanket approval cover repeated valid fixes, commits, pushes, replies,
  thread resolution, and gated merges into the integration branch.
- Require explicit human approval before merging the integration branch into the
  protected/default branch.

Do not choose direct default-branch promotion silently. If the user wants that,
confirm the authorization scope and merge gates first.

## Workflow

1. Define the branch topology.
   - Identify source branches or PRs.
   - Identify or create `integration/<feature-name>`.
   - For each existing PR, verify its base branch is `integration/<feature-name>`
     before closeout delegation.
   - If an existing PR targets the default branch, retarget it to the integration
     branch or create a new integration-targeted PR before delegating.
   - If a source branch has no PR, create an integration-targeted PR or block
     until the user explicitly defines separate branch-only gates.

2. Define gates.
   - Approval must be fresh for each PR's current head SHA and PR body.
   - Required remote checks must be green for each current head.
   - Local tests must pass before each merge into integration.
   - No unresolved actionable review feedback may remain.
   - No unrelated local/user changes may be staged, committed, overwritten, or
     hidden.

3. Dispatch closeout work.
   - For each concrete PR whose base is `integration/<feature-name>`, invoke
     `pr-closeout-loop` with target branch set to `integration/<feature-name>`.
   - Keep each loop scoped to its own PR.
   - If a loop finds conflicting feedback, stale authorization, or missing
     validation, mark that item blocked instead of widening scope.

4. Maintain the integration branch.
   - Merge completed branches with normal merge commits by default.
   - Re-run integration-level validation after merges when the repository has a
     suitable suite or workflow.
   - If integration validation fails, triage whether the failure belongs to a
     just-merged branch, branch interaction, or environment.

5. Prepare human checkpoint.
   - Summarize branches/PRs included, commits merged, review feedback resolved,
     validation run, CI state, deferred low findings, and known risks.
   - Do not merge the integration branch into the default branch until the user
     explicitly approves that promotion.

## Blocking Conditions

Block orchestration when:
- branch topology is ambiguous and a safe default is not obvious;
- blanket approval scope is unclear;
- any PR lacks fresh approval or required green checks;
- integration validation fails and cannot be attributed safely;
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
