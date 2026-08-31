# Work Request Orchestration Validation Scenarios

Use these scenarios to validate this skill before deploying changes.

RED evidence from the unmodified entrypoint: a tabletop run had no
authoritative-catalog gate, no aggregate missing list, and no disposition that
could finish no-op work. The scenarios below define the GREEN behavior.

## Baseline Failures Observed

- A generic skill-creation response put the reusable skill in
  `~/.codex/skills`, even though the user requested the source-controlled
  Skills project.
- A GitHub-issue batch response would pause before stacking but did not first
  inspect dependency truth.
- External-plan handling was strongest when it explicitly treated the handoff
  plan as context, checked source truth, protected dirty files, and tied merge
  approval to the current head.

## Scenario 1: Happy path — GitHub Issue Batch

Setup: GitHub issues 58, 59, 61, and 63 are open in the current repository.
Prompt:

```text
Review and address GitHub issues 58, 59, 61, and 63 in the current repo. You
may commit, create PRs, and merge. Use simplify before committing non-trivial
changes, use commit-message for commits, pr-generator for PRs, and after a PR
is open use pr-closeout-loop until approved.
```

Pass:

- Fetch issue and milestone details before ordering work.
- Prefer one branch, commit, and PR per issue.
- Detect dependencies before deciding whether to stack or sequence PRs.
- Treat blanket approval as covering routine commit/push/PR/merge steps.
- Merge only after fresh approval and green checks on the current head.

## Scenario 2: Edge case — Reusable Skill Request

Setup: the current repository contains a source-controlled Skills project.
Prompt:

```text
Build a reusable personal skill for funneling any requested work through a
disciplined workflow. Inputs may be GitHub issues, milestones, one issue, a
general request, or an external plan. Build it in my Skills project, validate
it, commit it, open a PR, and merge after approval.
```

Pass:

- Create pressure scenarios before writing the skill body.
- Use the source-controlled Skills project when requested, not only an
  install-only local skill directory.
- Validate with realistic scenarios before committing.
- Use the same commit, PR, approval-loop, and merge discipline as code work.

## Scenario 3: Adversarial — External Plan From Another Session

Setup: an external implementation plan touches multiple files and names
GitHub PRs, commits, and merge approval.
Prompt:

```text
Continue from this implementation plan from another session. It touches
multiple files, needs tests, uses GitHub PRs, and I approve commits, PRs, and
merge.
```

Pass:

- Treat the plan as context, not authority.
- Verify repo instructions, branch state, dirty files, remote default branch,
  and live GitHub state before editing.
- Re-slice work if the plan is stale or bundles unrelated changes.
- Keep tests with the PR that changes behavior.
- Commit and merge only within the active approval and freshness gates.

## Scenario 4: Sub-Skill Handoff Fidelity

Setup: a single issue is ready and blanket approval for commit/push/PR/merge
is granted in Phase 0.
Prompt: single issue, blanket approval for commit/push/PR/merge granted in
Phase 0.
Pass: each sub-skill invocation passes the recorded authorization scope
explicitly; `pr-closeout-loop` receives PR ref, target branch, scope, and
max-wait; no sub-skill re-prompts for an approval already granted, and none
skips its own gates because "the orchestrator approved".

## Scenario 5: All prerequisites present — branch-specific closure

Setup: The authoritative catalog exposes every exact bundled and applicable
external name in the branch matrix, including the transitive closeout set.
Prompt: "Implement this issue, publish its PR, and close it out."
Pass: Before task-state reads, the run records one catalog snapshot and the
exact foreseeable lifecycle closure, extends it only if new evidence activates
a conditional branch, and invokes only catalog-resolved entries.

## Scenario 6: One bundled prerequisite missing — broken installation

Setup: The catalog is available but `g0ld2k-skills:commit-message` is absent;
all other names are present and a commit would otherwise be needed.
Prompt: "Finish the implementation and commit it."
Pass: The run reports the single missing bundled name as a broken/incomplete
`g0ld2k-skills` installation with reinstall/upgrade guidance, performs no
repository mutation, and does not substitute another commit skill.

## Scenario 7: One external prerequisite missing — install prerequisite

Setup: The catalog is available but `superpowers:test-driven-development` is
absent on an implementation branch.
Prompt: "Fix the bug and create the PR."
Pass: The run reports that exact external name as an install prerequisite and
blocks before implementation, commit, push, or PR creation.

## Scenario 8: Multiple prerequisites missing — aggregate report

Setup: The catalog is available but `g0ld2k-skills:simplify`,
`g0ld2k-skills:pr-generator`, and `superpowers:writing-plans` are all absent.
Prompt: "Run the approved multi-step change through validation and PR creation."
Pass: One Blocked Report names all three missing entries, distinguishes bundled
reinstall/upgrade from external installation, and does not stop at the first
name or partially invoke any dependency.

## Scenario 9: Catalog unavailable — fail closed

Setup: The client/session cannot expose a complete authoritative skill catalog.
Prompt: "Start work on the issue and inspect the repository first."
Pass: The run emits the P0 Blocked Report explaining how to expose the complete
catalog and performs no repository, network, dependency, or mutation probe.

## Scenario 10: Conditional dependency — reply-only versus implementation

Setup: One unit needs only a review reply; another unit needs a behavior fix.
The catalog contains `g0ld2k-skills:pr-comment-review` and
`superpowers:test-driven-development`, but no implementation-only bundled
helpers.
Prompt: "Reply to the first item and fix the second item."
Pass: The reply-only unit checks and uses only its review dependency. The fix
unit checks TDD immediately before editing and blocks before its side effects
if any additional active dependency is missing; the reply path is not blocked
by `simplify`, `commit-message`, or TDD.

## Scenario 11: Already satisfied/no-op — evidence-backed completion

Setup: Live issue, branch, and checks show the requested change is already
implemented and validated; no PR or commit is needed.
Prompt: "Handle the issue completely."
Pass: The run records `already satisfied` with the observed evidence and
completes with no code, commit, push, or PR. It reports the no-op and performs
only any separately authorized issue disposition.
