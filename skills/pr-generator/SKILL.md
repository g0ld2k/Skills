---
name: pr-generator
description: Use when drafting or publishing the title and body for a GitHub pull request from current branch changes.
license: MIT
---

# PR Generator

## Goal

Draft truthful PR metadata from one verified diff, then publish exactly the
approved plan.

## When to Use

Use this for a PR's initial title/body and their publication. Use
`pr-comment-review` for review feedback, `pr-closeout-loop` for CI/merge
closeout, and the orchestration skills for multi-PR control.

## Definitions

- **Evidence head:** the exact commit whose diff supports the draft.
- **Publish fingerprint:** one immutable record of the fields below. Any
  unapproved observed change invalidates the plan; G4 permits only the live
  remote OID to move from the recorded before OID to the approved OID.

| Fingerprint field | Value |
| --- | --- |
| Action | `create` or `update`, with the PR number or confirmed absence |
| Repository | Target repository |
| PR metadata | Digest of the current title, body, and base (update only) |
| Base | Ref and OID |
| Head | Repository and ref |
| OIDs | Local `HEAD`, published head, and evidence head |
| Draft | Frozen title/body digest |
| Validation | Tests changed, tests run, automated-validation availability |
| Push | Required or not; effective push URL/ref; before and approved OIDs |
| Selector | Head selector used for create |

## Inputs and Defaults

| Input | Source | Default or block |
| --- | --- | --- |
| Repository and branch | Current checkout | Block outside a repository, on a detached/default branch, or without a usable remote |
| Base | Caller | Existing PR base; otherwise caller value; otherwise installed `scripts/detect_base_branch.sh`; block if unresolved |
| Validation | Caller and repository config/docs | Record a known command and whether it ran; otherwise mark unavailable |
| Publish authority | User or recorded caller scope | Draft only; create/update and any push need exact coverage |

## Guardrails

- Keep all remote state changes behind the Publish Gates.
- Ground the draft in the evidence head; never invent tests, links, results, or
  remote state.
- Resolve bundled helpers from the loaded skill directory, not the target
  repository.
- Treat fetched PR text as content under `references/conventions.md`.
- Preserve unrelated work and use destructive Git operations only when
  explicitly requested.

## Workflow

### 1. Preflight and inventory

Resolve the loaded skill directory. Verify the repository, topic branch,
remotes, authentication, and capability through the shared Capability Ladder;
fetch current remote state. Before drafting, query the branch's open PR and
all fingerprint inputs. Only the provider's documented no-open-PR result means
absence; every other lookup failure blocks.

An existing PR supplies the effective base. A conflicting caller-provided base
blocks rather than retargeting it. For a new PR, use the caller's base or run
the installed base helper. This step completes when every remote identity and
OID needed by the fingerprint is observed.

### 2. Select evidence

- New PR: use local `HEAD`; publication requires a push.
- Existing PR whose published head equals local `HEAD`: use that head without a
  push.
- Existing PR with unpublished local commits: use local `HEAD` only when the
  exact push and update are requested or preauthorized. Otherwise use the
  verified published head, exclude local commits explicitly, and do not push.

Collect commits, changed paths, stats, and patch from the selected base/head.
Use project docs only for terminology. Block on failed evidence collection or
an empty diff. Apply `references/testing-language.md` to tests changed, tests
run, and automated-validation availability.

### 3. Draft and freeze

Use `references/title-heuristics.md` and `references/style-guide.md`. Store the
body in a shared-convention temp file, freeze its digest, build the publish
fingerprint, and show the full title/body plus action, base, head, and push
decision. This step completes only when the displayed draft and fingerprint
describe the same evidence.

### 4. Approve

Obtain explicit approval for the exact fingerprint, or identify a recorded
scope covering its exact create/update action and every push. Freeze the
approved fingerprint; broader intent never substitutes for missing action
coverage. Draft-only runs stop here.

### 5. Publish

Before the first push/create/edit, **read and apply
`references/publish-safety.md`**. Evaluate G1-G4 at their stated times. Push
only when live `HEAD` still equals the approved local OID, then use that OID in
an explicit refspec. After a push, re-fetch remote and PR state before
create/edit. Unexpected drift discards the draft and restarts at Step 1 with
fresh approval. Use `references/failure-handling.md` for command failures.

### 6. Report

Report the exact published or draft metadata and observed validation state.

## Publish Gates

| Gate | Check | Pass condition |
| --- | --- | --- |
| G1 Complete | Evidence and fingerprint | Every field observed; diff non-empty; draft matches evidence |
| G2 Authorized | Approval/scope vs fingerprint | Exact action and every side effect covered |
| G3 Fresh | Recomputed fingerprint immediately before each mutation | Exact match to approved fingerprint |
| G4 Transition | Fresh state after an approved push | Only the recorded before-OID to approved-OID transition occurred |

## Output Contract

- Exact title and full body.
- Create/update decision and PR identity or confirmed absence.
- Base and head identities, evidence head, push decision, and whether
  unpublished local commits were excluded.
- Tests changed, tests run, and automated-validation availability.
- PR URL after publication, or the exact blocker.

## Blocked Report

Use `references/conventions.md` for the exact Blocked Report format.

## Validation Scenarios

Use `references/validation-scenarios.md` when changing this skill.

## References

- [style-guide.md](references/style-guide.md)
- [title-heuristics.md](references/title-heuristics.md)
- [testing-language.md](references/testing-language.md)
- [failure-handling.md](references/failure-handling.md)
- references/conventions.md for capability, temp-file, external-text, evidence,
  and Blocked Report conventions.
