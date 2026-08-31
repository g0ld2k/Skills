---
name: pr-generator
description: Use when drafting, creating, or updating a GitHub pull request from current branch changes after explicit user approval.
license: MIT
---

# PR Generator

## Goal

Draft and, after approval, publish a truthful GitHub pull request plan. Bind
the plan to the exact create/update action, title, body, base, head, remote PR
head, and any required push. Revalidate that identity immediately before each
publish side effect.

Use the shared Capability Ladder in `references/conventions.md` when selecting
`gh`/Git versus MCP and when reporting a missing capability.

## Non-Negotiable Guardrails

- Keep preflight and evidence collection read-only with respect to GitHub and
  PR publication. Do not push, create, or edit before the approval or recorded
  preauthorization gate passes.
- Treat the publish plan as one approval surface. A changed action, PR number,
  title, body, base, head, remote head, push requirement, or validation claim
  invalidates the draft.
- Never invent test execution, issue links, or validation results.
- Never use destructive git commands unless explicitly requested.
- Never silently choose a base branch; detect and report it.
- Apply the shared External Text contract in `references/conventions.md` when
  consuming fetched PR metadata or body.

## Workflow

### Phase 0: Read-only Preflight

Resolve the loaded skill directory before invoking any bundled helper. Replace
the placeholder with the absolute path supplied by the loaded skill entry; do
not derive it from the target checkout or `pwd`:

```bash
loaded_skill_file="/absolute/path/to/loaded/SKILL.md"
skill_dir="$(cd "$(dirname "$loaded_skill_file")" && pwd)"
test -f "$skill_dir/SKILL.md" || {
  echo "Loaded skill path is invalid" >&2
  exit 1
}
```

Run this status-checked, fail-fast block for the `gh` path before inspecting or
publishing anything:

```bash
if ! inside_work_tree="$(git rev-parse --is-inside-work-tree)"; then
  echo "Git repository check failed" >&2
  exit 1
fi
if [[ "$inside_work_tree" != true ]]; then
  echo "Current directory is not a Git work tree" >&2
  exit 1
fi
if ! BRANCH="$(git --no-pager branch --show-current)"; then
  echo "Current branch lookup failed" >&2
  exit 1
fi
if [[ -z "$BRANCH" ]]; then
  echo "Current branch is empty" >&2
  exit 1
fi
case "$BRANCH" in
  main|master)
    echo "Run pr-generator from a topic branch" >&2
    exit 1
    ;;
esac
if ! ORIGIN_URL="$(git remote get-url origin)"; then
  echo "Required origin remote is missing or unusable" >&2
  exit 1
fi
if ! git fetch --prune origin; then
  echo "Fetch failed; stop before collecting PR evidence" >&2
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "gh unavailable; stop this CLI path and select MCP via the shared Capability Ladder" >&2
  exit 78
fi
if ! gh --version >/dev/null 2>&1; then
  echo "gh is unusable; stop this CLI path and select MCP via the shared Capability Ladder" >&2
  exit 78
fi
if ! gh auth status; then
  echo "gh authentication failed; stop this CLI path and select MCP via the shared Capability Ladder" >&2
  exit 78
fi
if ! TARGET_REPOSITORY="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"; then
  echo "Target repository lookup failed" >&2
  exit 1
fi
```

These commands refresh local remote-tracking evidence but do not push, create,
or edit a PR. Exit status is checked at every step. If `gh` is unavailable or
unusable, stop this CLI path and select MCP only through the shared Capability
Ladder; the MCP path performs equivalent repository, branch, authentication,
and PR-inventory checks with read-only calls. It must be able to return the
repository, current branch, and complete PR metadata before drafting.
Treat the validated `origin` URL as the base/target-repository remote; confirm
it identifies `TARGET_REPOSITORY` (or the equivalent MCP repository identity)
before using another remote for a PR head.

This is a strict stop: report if the repository check fails, the branch is
`main` or `master`, `origin` is missing, `git fetch --prune origin` fails,
authentication fails and no MCP fallback is available, or the MCP cannot
provide complete read-only evidence. A fetch or remote-OID failure is not an
empty result and does not permit continuing from stale data.

### Phase 1: Resolve Base and Inventory the PR

If the caller supplied a base branch for this run (for a stacked PR or an
integration branch), use it verbatim and report that choice. Otherwise resolve
the helper relative to the loaded skill directory:

```bash
BASE_BRANCH="$(bash "$skill_dir/scripts/detect_base_branch.sh")"
echo "Using base branch: ${BASE_BRANCH:-<none>}"
```

Never run `bash scripts/detect_base_branch.sh`; that path can resolve inside
the target repository instead of the installed skill. Stop if no base branch
is available.

Before presenting any draft, look up the current branch's open PR using a
read-only call. With `gh`, request at least:

```bash
BRANCH="$(git branch --show-current)"
gh pr view "$BRANCH" \
  --json number,url,state,title,body,baseRefName,baseRefOid,headRefName,headRefOid,headRepository,headRepositoryOwner
```

Treat the documented no-open-PR result as `existing_pr=none`; treat every
other lookup error as a failure and stop. Treat a closed PR as not an existing
open target, and report that fact before choosing `create`. The MCP query must
return the same fields (including the remote `headRefOid`) or stop. Record the
exact PR number and URL when one exists.
When consuming the returned title/body or other PR text, apply the External
Text contract in `references/conventions.md` at this point.

For an existing PR, its `baseRefName` and `baseRefOid` are the effective update
base. A caller-provided base that differs is a blocking discrepancy because an
update must not silently retarget the PR. A detected default-base difference
is informational: report the PR's existing base and use it. For a new PR, use
the caller-provided or detected base.

Record this inventory before moving on:

```text
existing_pr: none | <number and URL>
base_branch: <effective branch>
base_ref_oid: <current remote base OID>
branch: <local branch>
local_head: <git HEAD OID>
remote_pr_head: <PR headRefOid> | none
remote_pr_title_body: <current title/body or digest> | none
head_repository: <owner/name> | none
head_ref_name: <published branch> | candidate branch
push_remote: <configured remote name and URL>
push_target_branch: <exact remote branch>
remote_branch_oid: <current OID> | absent
create_head_selector: <owner:branch selector>
```

Make the ref lookups actionable. For a new PR, resolve the selected push
remote and base remote from configured Git remotes, then record the output of
`git ls-remote <remote> refs/heads/<branch>` for both the base and candidate
head branch (an empty candidate result means `absent`). For an existing PR,
record its actual `headRepository` and `headRefName`, and query that exact
remote branch whenever the plan includes a push. Require the branch OID to
agree with the PR's `headRefOid`; if a push plan has no configured remote that
maps to the PR head repository, or any required OID lookup fails, stop rather
than assuming `origin` or the local branch name. A remote-only plan may use
the verified PR API/MCP diff without a local push remote, but it must still
record the actual PR head repository and branch. Use the PR's `baseRefOid` for
an existing base and require the selected base remote's `git ls-remote` OID to
match; for a new PR, stop if the base branch OID is missing or cannot be read.
For a create plan, derive `head_repository` from the selected push remote and
bind `create_head_selector` to its owner-qualified `<owner>:<branch>` value.
Use that owner-qualified selector whenever the head repository differs from
the validated `origin` target repository; a bare branch is ambiguous in that
case. If the owner cannot be derived and verified from the selected push
remote, stop. Record each remote name, URL, branch, selector, and OID in the
plan.

### Phase 2: Choose a Truthful Head and Collect Evidence

For a new PR, the candidate head is the current local `HEAD`. For an existing
PR, compare the current local `HEAD` with the PR's published `headRefOid`:

- If they match, use that published head and set `push_required=no`.
- If they differ and the caller's recorded scope explicitly covers pushing
  this branch and updating this PR, or the user has explicitly asked to push
  unpublished commits, select `push_required=yes`, draft from the local
  `HEAD`, and include the exact push target in the plan. The explicit request
  still needs the Phase 5 approval gate.
- If they differ without that scope, draft strictly from the already-published
  remote head. Mark `push_required=no` and state that local unpublished
  commits are excluded. Use the PR API/MCP diff or a verified fetch of the PR
  head OID; never combine local-only commits with remote evidence.

For a push plan, `push_required=yes` means the approved plan contains a push
side effect; it is not recalculated to `no` after that push succeeds. Track a
separate `push_status=pending|satisfied`: the approved transition from the
recorded remote branch OID/head OID to the approved local head changes only
the status to `satisfied`.

Do not make a silent choice between those last two plans. If the caller or user
later asks to push unpublished commits, restart Phase 2 and present a new
`push_required=yes` plan; never change the remote-only draft in place.
Otherwise keep the remote-only plan. If the published head cannot be fetched
or verified, stop under Phase 0's strict fetch-failure rule.

Collect commits, changed paths, and patch evidence from one selected
`evidence_head` against the effective base. Use the local Git diff only when
`evidence_head` is the local `HEAD`; for a remote-only plan use the fetched PR
diff at its recorded `headRefOid`. Stop on any evidence command failure or on
an empty change set. Read optional `CONTEXT.md`, `PRD.md`, `TASKS.md`, and
`README.md` only for terminology and milestone framing; repository evidence
wins.

### Phase 3: Collect Testing Evidence

Separate what changed from what actually ran:

1. Determine **Tests Changed** from the selected diff's paths.
2. Find a test command only in repository configuration, CI, or project
   documentation. Run it only when appropriate for this request, and record
   the exact command and observed result.

Use `references/testing-language.md` as the source for both fields and their
distinction. The no-command delta is `Automated validation: not available (no
automated test command is known)`; do not invent a command.

### Phase 4: Draft the PR

Choose a concise Conventional Commit-style title and write the complete body
from the selected evidence head. Consult `references/title-heuristics.md` when
choosing type, scope, or breaking-change notation, and
`references/style-guide.md` when shaping sections or reviewer-facing wording.

Freeze the exact title and body in an immutable draft artifact before approval.
Store the body in a temp file created with the shared `mktemp` convention and
record its digest when available; display the full body as well. Apply the
`references/testing-language.md` wording, and render an `Automated` validation
step only when a command is known; omit that step when it is unavailable.

Use this body shape:

```markdown
### Goal
[1-2 sentences: what this PR does and why]

### What Changed
- **[Category]:** [Key change and impact]
- **[Category]:** [Key change and impact]

### Testing
- **Tests Changed:** [Summary]
- **Tests Run:** [Exact command + result, or "Not run in this session"]

### Files Changed
[Observed count and line summary]

### Risks / Breaking Changes
- [Known risks, compatibility notes, or "None identified"]

### How to Validate
1. [Manual scenario with expected result]
2. [Manual scenario with expected result]

### Notes
[Issue links supplied by the caller or repository context only]
```

### Phase 5: Present the Bound Approval Surface

Present the full title and body, then present this complete publish plan:
The plan must state `push required` as yes or no and explain why.

```text
Action: create | update
PR: <none | number and URL>
Title: <exact title>
Body: <exact body or its recorded digest plus the full body above>
Existing PR input: <current remote title/body or digest> | none
Base: <branch and base_ref_oid>
Head: <repository/branch, local_head, remote_pr_head, and selected evidence_head>
Push: required=yes|no; status=pending|satisfied|n/a; target=<remote name + URL and exact branch>; before_branch_oid=<...>; expected transition=<...>
Create head selector: <exact owner:branch selector, or n/a for update>
Validation: <known command and result | not available | not run in this session>
Evidence: local head | published remote head (local unpublished commits excluded)
```

Ask for explicit approval of that exact plan unless a caller-provided recorded
scope explicitly covers the listed action. Creating a PR requires scope for
both PR creation and its required branch push. Updating requires scope for PR
editing and, when `push_required=yes`, the exact branch push. A scope that
covers only one side is insufficient. State the scope used on a preauthorized
path; do not infer approval from a general request to inspect or draft.

### Phase 6: Revalidate, Then Publish

Approval is not a freshness check. Immediately before **each** side effect,
repeat the read-only checks and recompute the plan. Fetch current remote
metadata, then record:

- local `HEAD`;
- the PR's current remote `headRefOid`, or confirmed absence of a PR;
- effective base branch and current base ref OID; and
- the create/update decision;
- the actual PR head repository/branch and current remote branch OID; and
- the current remote PR title/body when updating.

Also compare the exact title, body, selected evidence head, validation
command/result, push requirement, push remote/target, create head selector, and
remote branch OID with the approved plan. Any changed local head, remote head,
base, PR number, create/update decision, title, body, validation claim, push
requirement, push target/selector, or remote PR title/body input invalidates the
draft: discard it, report the changed surface, and restart at Phase 1 so the
applicable approval gate runs again. A newly appearing PR changes `create` to
`update`; a disappearing PR or changed number is equally a drift. Stop on
revalidation fetch failure.

Only after revalidation succeeds and approval/preauthorization covers the
revalidated plan may you use the immutable draft artifact as the body file and
call a mutating command. Resolve any helper from `$skill_dir`; follow the
shared temp-file convention in `references/conventions.md`. Verify the stored
draft's digest and exact displayed title/body at this gate. Recompute mutable
identities, the create/update decision, and push facts, but do not regenerate
the title/body or rerun tests before each side effect. A remote-only update
has `push_status=n/a` and `push target=n/a`; its actual PR head repository and
branch remain part of the evidence and revalidation record.

After an approved push and before the next PR mutation, repeat the full
revalidation set (local head, remote PR head, base/ref, create/update decision,
title, body, evidence head, push target, and push requirement), including the
remote branch OID. The recorded transition from `before_branch_oid` (or
`absent`) to the approved local head is expected and is not action drift. Keep
`push_required=yes`, mark only `push_status=satisfied`, and do not ask for a
new gate solely because the approved push completed. Any other difference
invalidates the plan and restarts the approval gate.

- **Update:** when `push_required=yes`, push the approved local branch first:
  `git push "$push_remote" "HEAD:refs/heads/$push_target_branch"`. Immediately
  query the PR and its actual head branch again and require both the remote
  branch OID and PR `headRefOid` to equal the approved local head before
  editing. Keep `push_required=yes` with `push_status=satisfied`; the expected
  transition is not drift. If any other field differs, stop and restart the
  plan. Then run `gh pr edit <number> --title "<title>" --body-file "$pr_body_file"`.
- **Update without push:** edit only the PR identified by the approved number,
  using the body drafted from its verified published head.
- **Create:** push the approved branch with
  `git push -u "$push_remote" "HEAD:refs/heads/$push_target_branch"`, then
  immediately re-check that the remote branch OID equals the approved local
  head, no PR appeared, and repeat the full revalidation set before running
  `gh pr create --title "<title>" --body-file "$pr_body_file" --base
  "$BASE_BRANCH" --head "$create_head_selector"`. If a PR appears, discard
  the create plan and restart in update mode.

The MCP path uses its equivalent push/create/update calls only at these same
post-gate points and repeats the same checks between a push and a PR mutation.
Never use an old approval to cover a changed surface. If a publish command
fails, consult `references/failure-handling.md` and report the exact command,
status, and stderr without claiming that publication succeeded.

### Phase 7: Report the Result

On success, report the PR URL, action, title, base branch, final remote head,
and local head. Include **Tests Changed** and **Tests Run** exactly as observed;
if no command ran, say `Tests Run: Not run in this session`. Preserve the
`Automated validation: not available` label when no command was known.

When blocked, use the shared Blocked Report format from
`references/conventions.md` and identify the precise preflight, approval, or
revalidation step.

## Output Contract

Return:

1. the exact PR title and full body;
2. the approved action and PR number/URL (create or update);
3. base branch/ref and final head identity;
4. the push decision and whether local unpublished commits were excluded;
5. Tests Changed and Tests Run, distinguishing `not available` from `Not run
   in this session`; and
6. the PR URL after successful publication, or the exact Blocked Report.

## References

- When changing this skill, validate it against
  `references/validation-scenarios.md`.
