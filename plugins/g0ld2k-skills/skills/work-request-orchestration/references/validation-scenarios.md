# Work Request Orchestration Validation Scenarios

Use these scenarios to validate this skill before deploying changes.

## Baseline Failures Observed

- A generic skill-creation response put the reusable skill in
  `~/.codex/skills`, even though the user requested the source-controlled
  Skills project.
- A GitHub-issue batch response would pause before stacking but did not first
  inspect dependency truth.
- External-plan handling was strongest when it explicitly treated the handoff
  plan as context, checked source truth, protected dirty files, and tied merge
  approval to the current head.

## Scenario 1: GitHub Issue Batch

Prompt:

```text
Review and address GitHub issues 58, 59, 61, and 63 in the current repo. You
may commit, create PRs, and merge. Use simplify before committing non-trivial
changes, use commit-message for commits, pr-generator for PRs, and after a PR
is open use pr-closeout-loop until approved.
```

Expected behavior:

- Fetch issue and milestone details before ordering work.
- Prefer one branch, commit, and PR per issue.
- Detect dependencies before deciding whether to stack or sequence PRs.
- Treat blanket approval as covering routine commit/push/PR/merge steps.
- Merge only after fresh approval and green checks on the current head.

## Scenario 2: Reusable Skill Request

Prompt:

```text
Build a reusable personal skill for funneling any requested work through a
disciplined workflow. Inputs may be GitHub issues, milestones, one issue, a
general request, or an external plan. Build it in my Skills project, validate
it, commit it, open a PR, and merge after approval.
```

Expected behavior:

- Create pressure scenarios before writing the skill body.
- Use the source-controlled Skills project when requested, not only an
  install-only local skill directory.
- Validate with realistic scenarios before committing.
- Use the same commit, PR, approval-loop, and merge discipline as code work.

## Scenario 3: External Plan From Another Session

Prompt:

```text
Continue from this implementation plan from another session. It touches
multiple files, needs tests, uses GitHub PRs, and I approve commits, PRs, and
merge.
```

Expected behavior:

- Treat the plan as context, not authority.
- Verify repo instructions, branch state, dirty files, remote default branch,
  and live GitHub state before editing.
- Re-slice work if the plan is stale or bundles unrelated changes.
- Keep tests with the PR that changes behavior.
- Commit and merge only within the active approval and freshness gates.
