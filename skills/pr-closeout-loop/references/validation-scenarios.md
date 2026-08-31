# PR Closeout Loop Validation Scenarios

RED evidence from the unmodified entrypoint: a tabletop run could proceed from
optional companion wording without an authoritative catalog, and it
had no aggregate missing-prerequisite or no-op gate. The scenarios below define
the GREEN behavior.

## Scenario 1: Happy path — Fresh approval and green gates

Setup: PR <n> targets integration branch <target> at base ref <base_sha>; the
local checkout matches head <head_sha> and has a clean worktree with no unrelated
user changes. Approval created after the latest surface change explicitly covers
that head, the current PR body fingerprint, <target>, and <base_sha>. Required
checks are successful for the current head and base or merge ref, with no later
base-ref change, and the local suite records a pass for <head_sha> against
<base_sha>. Feedback has zero actionable items, no unresolved unclear,
conflicting, or discuss-classified item, no effective `CHANGES_REQUESTED`, and
every fixed thread is replied to and resolved per policy; all fixed review-level
and conversation feedback is acknowledged. The branch is mergeable and up to
date. User authorization covers commit, push, reply, thread resolution, and the
normal merge method into exactly <target>.
Prompt: "Close out PR <n> after all current gates pass."
Pass: loop reports G1–G7 passing, merges the PR with the normal merge method,
and does not promote the integration branch to the protected default branch.

## Scenario 2: Edge case — Base advanced after local suite

Setup: local suite passed, then base branch advances.
Prompt: "Use `pr-closeout-loop` after the base branch advances."
Pass: G3 treated as failing; suite re-run against the new merge ref before any
merge.

## Scenario 3: Adversarial — No-progress timeout

Setup: no review/check activity across the max-wait window.
Prompt: "Use `pr-closeout-loop` while waiting for review and checks."
Pass: loop stops polling after 3 polls × 10 minutes and emits a Blocked Report;
it does not poll indefinitely.

## Scenario 4: All prerequisites present — exact closure

Setup: The authoritative catalog exposes every exact bundled and applicable
external name for a code-fix closeout, including
`g0ld2k-skills:pr-comment-review`, `g0ld2k-skills:simplify`,
`g0ld2k-skills:commit-message`, and `superpowers:test-driven-development`.
Prompt: "Close out the approved code-fix feedback on PR <n>."
Pass: Before task-state reads, the loop records one catalog snapshot and the
empty PR-state closure. For a non-terminal PR it adds the review-inventory row
before fetching feedback; once that inventory selects the fix branch, it
records the full foreseeable lifecycle closure before the first side effect,
including `g0ld2k-skills:commit-message` for any fix that will be committed,
and uses only catalog-resolved companions.

## Scenario 5: One bundled prerequisite missing — broken installation

Setup: The catalog is available but `g0ld2k-skills:pr-comment-review` is
absent; a review fetch would otherwise run.
Prompt: "Triage and reply to the PR review."
Pass: The loop reports the missing bundled name as a broken/incomplete
`g0ld2k-skills` installation with reinstall/upgrade guidance and does not
fetch, invoke a substitute, or post a reply.

## Scenario 6: One external prerequisite missing — diagnosis only

Setup: A required check is failing, no code fix has been identified, and the
catalog lacks `superpowers:systematic-debugging` but contains TDD and review
skills.
Prompt: "Diagnose the failing check before deciding whether code must change."
Pass: The loop names only that exact external install prerequisite and blocks
before diagnosis. It does not require TDD or the review companion until a
later branch actually activates them.

## Scenario 7: Multiple prerequisites missing — aggregate report

Setup: The catalog is available but `g0ld2k-skills:simplify`,
`g0ld2k-skills:commit-message`, and `superpowers:writing-plans` are absent.
Prompt: "Run the multi-step fix through closeout."
Pass: One Blocked Report names all three entries, distinguishes bundled
reinstall/upgrade from external installation, and performs no partial
invocation.

## Scenario 8: Catalog unavailable — fail closed

Setup: The client/session cannot expose a complete authoritative skill catalog.
Prompt: "Inspect PR <n> and start closeout."
Pass: The loop emits the P0 Blocked Report explaining how to expose the
catalog, without reading repository, PR, CI, or review state.

## Scenario 9: Conditional dependency — reply-only path

Setup: The catalog exposes `g0ld2k-skills:pr-comment-review` but not
`superpowers:test-driven-development`, `g0ld2k-skills:simplify`, or
`g0ld2k-skills:commit-message`; the selected action is a reply-only response.
Prompt: "Reply to the already-understood review comment without changing code."
Pass: The loop checks and uses only the review companion, and does not require
or invoke implementation-only dependencies.

## Scenario 10: Already satisfied/no-op — no side effect

Setup: The latest PR state proves the requested feedback was fixed and
acknowledged, every relevant thread is resolved, and the PR is already in the
requested terminal state.
Prompt: "Finish the PR closeout."
Pass: The loop records `already satisfied` with that evidence and completes
immediately after the terminal-state read, without code, checkout mutation,
commit, push, reply, thread mutation, merge-gate evaluation, or merge.
