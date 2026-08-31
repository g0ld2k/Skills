# Integration Branch Orchestrator Validation Scenarios

RED evidence from the unmodified entrypoint: a tabletop run could delegate to
`pr-closeout-loop` without first checking a client catalog, aggregating missing
transitive dependencies, or recognizing a no-change validation path. The
scenarios below define the GREEN behavior.

## Scenario 1: Happy path — Existing in-scope integration branch

Setup: `integration/feature-x` exists on the remote from the recorded protected
base, its current commits are in this run's scope, one source PR targets it, and
branch creation, PR closeout delegation, and integration merges are authorized.
Prompt: "Use `integration-branch-orchestrator` to prepare the branch and
delegate closeout for the PR."
Pass: verifies ancestry, scope, and the remote tip; delegates the integration-
targeted PR to `pr-closeout-loop`, then runs integration validation after the
delegated merge without promoting to the protected default branch.

## Scenario 2: Edge case — PR targeting default branch

Setup: source PR targets `main`; retargeting authorized.
Prompt: "Use `integration-branch-orchestrator` to route the PR to integration/feature-x."
Pass: retargets to the integration branch (prefer retarget over clone) before
delegating.

## Scenario 3: Adversarial — Delegated merge landed remotely

Setup: closeout loop merged via GitHub; orchestrator's checkout is stale.
Prompt: "Use `integration-branch-orchestrator` to validate the merged integration branch."
Pass: fetches the remote integration tip before running integration validation.

## Scenario 4: Deterministic — two-PR stale-tip race

Setup: `integration/feature-x` is at remote tip `I0`; PRs A and B are both
active, target the branch, and have passed G1–G7 against `I0`. Separate
worktrees are available, normal merge commits are required, and one
integration-wide coordinator is available. At slot admission, A is ready and
selected for the first slot so the tip transition is deterministic; candidate
selection remains readiness-based rather than source-ordered.
Prompt: "Run parallel closeout preparation for A and B, then serialize their
integration merges with the coordinator and validate after each merge."
Pass:

1. Delegates both loops with merge authorization excluded.
2. The coordinator grants A a slot and records `slot_base_sha=I0`. Immediately
   before merging, A fetches the integration tip and live PR state, confirms
   the tip is still `I0`, performs `pr-closeout-loop`'s final G1–G7 evaluation
   against `I0`, and merges normally, producing `I1`.
3. Fetches and records `I1`, then passes integration validation before another
   slot is granted.
4. The coordinator marks B's earlier `I0` evidence stale, grants B the next
   slot, and records `slot_base_sha=I1`. B refreshes and revalidates against
   `I1`; immediately before merging, B fetches the tip and live PR state,
   confirms the tip is still `I1`, passes the final G1–G7 evaluation, and
   merges normally, producing `I2`.
5. Fetches and records `I2` and passes integration validation before reporting
   promotion readiness.

The ledger proves that A and B never both pass the final merge gate against the
same stale tip `I0`, and records both post-merge validation results.

## Scenario 5: All prerequisites present — topology and delegation

Setup: The authoritative catalog exposes every exact bundled and applicable
external name for topology, PR creation, and delegated closeout.
Prompt: "Prepare integration/feature-x and delegate its PR for closeout."
Pass: Before task-state reads, the orchestrator records one catalog snapshot
and the empty topology-read closure. Once live topology shows action remains,
it records the full foreseeable lifecycle closure before the first side effect
and delegates only catalog-resolved skills.

## Scenario 6: One bundled prerequisite missing — broken installation

Setup: The catalog is available but `g0ld2k-skills:pr-generator` is absent and
a source branch has no PR.
Prompt: "Create the integration-targeted PR for the source branch."
Pass: The orchestrator reports a broken/incomplete `g0ld2k-skills` installation
with reinstall/upgrade guidance and does not create a PR or substitute a
similarly named generator.

## Scenario 7: One external prerequisite missing — install prerequisite

Setup: The catalog is available but `superpowers:test-driven-development` is
absent for a delegated code-fix closeout.
Prompt: "Delegate the approved implementation fix through integration."
Pass: The orchestrator names that exact external install prerequisite and
blocks before delegation or any fix side effect.

## Scenario 8: Multiple prerequisites missing — aggregate report

Setup: The catalog is available but `g0ld2k-skills:pr-closeout-loop`,
`g0ld2k-skills:simplify`, and `superpowers:writing-plans` are absent, and one
delegated candidate needs an authorized multi-step, non-trivial fix and commit.
Prompt: "Run the multi-PR integration closeout, including that approved fix."
Pass: One Blocked Report names all three entries, distinguishes bundled
reinstall/upgrade from external installation, and does not partially invoke a
closeout loop.

## Scenario 9: Catalog unavailable — fail closed

Setup: The client/session cannot expose a complete authoritative skill catalog.
Prompt: "Inspect the integration branch before deciding what to merge."
Pass: The orchestrator emits the P0 Blocked Report explaining how to expose
the catalog and performs no repository, network, or branch-state read.

## Scenario 10: Conditional dependency — validation-only path

Setup: The integration branch has already merged its candidate and needs only
fresh integration validation; implementation helpers and closeout companions
are absent.
Prompt: "Validate the merged integration branch and report promotion readiness."
Pass: The orchestrator checks only the validation branch's empty dependency set,
does not require or invoke PR creation, closeout, simplify, or TDD skills, and
records the validation result.

## Scenario 11: Already satisfied/no-op — evidence-backed completion

Setup: The remote integration tip and post-merge validation already match the
requested promotion checkpoint; no topology or merge action remains.
Prompt: "Handle the integration run completely."
Pass: The orchestrator records `already satisfied` with the observed tip and
validation evidence and completes without creating, retargeting, delegating,
committing, pushing, or merging anything.
