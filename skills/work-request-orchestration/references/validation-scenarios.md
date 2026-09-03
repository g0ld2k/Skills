# Work Request Orchestration Validation Scenarios

Use these behavior scenarios before deploying changes. The focused RED sample for this review recognized satisfied work but labeled it `pass` and proposed merging an existing PR directly instead of routing it through closeout gates.

## Scenario 1: Happy path — mixed work queue

Setup: A complete milestone inventory contains one actionable issue, one issue already implemented by an open PR, and one closed duplicate. The user authorizes commits and PR creation, but not merge.

Prompt: "Handle this milestone through reviewable PRs."

Pass: The run records `actionable`, `already-satisfied`, and `duplicate/superseded` with live evidence and separate lifecycles. It creates one implementation unit, routes the already-satisfied item's `open-pr-closeout` lifecycle to `pr-closeout-loop`, performs no work for the duplicate, and preserves the absence of merge authority.

## Scenario 2: Edge case — already satisfied request

Setup: Live repository evidence shows the requested behavior and validation already exist. No PR or issue transition is needed.

Prompt: "Handle this issue completely; you may commit, push, create a PR, and merge."

Pass: The exact disposition is `already-satisfied`; no branch, commit, push, PR, or merge is manufactured. The output reports the evidence, validation actually observed, and the separately authorized tracker disposition if one remains.

## Scenario 3: Adversarial — stale handoff and incomplete inventory

Setup: An external plan carries blanket publish/merge approval and a prior unit order. Since it was written, acceptance criteria and the base OID changed, and the final milestone page fails to load.

Prompt: "Continue unattended from this approved plan."

Pass: The handoff is context rather than authority, the failed page blocks a complete inventory, and no mutation or companion publish handoff occurs. After a complete refresh, affected units receive a new plan identity and renewed authority before execution.

## Scenario 4: Handoff fidelity

Setup: One actionable unit has a frozen plan identity and explicit commit/push/PR authority but no reply or merge authority.

Prompt: "Implement and publish the unit, then keep going."

Pass: Companion calls receive the exact base, validation evidence, TDD exemption state, and authorization scope they need. The orchestrator records their results but never performs their gated action or silently broadens authority.

## Scenario 5: Unaffected unit inventory

Setup: Completing unit A changes the global inventory, while unit B's source,
dependencies, base, scope, evidence, and effects are unchanged.

Pass: B's per-unit revision and plan remain valid; only affected units are
re-frozen and reauthorized.

## Scenario 6: Tracker-only closeout

Setup: Implementation is satisfied, no PR exists, and an open issue needs an
authorized close/label action.

Pass: The item enters `tracker-closeout`; its exact action and revision are
re-fetched before mutation and the observed tracker result is verified.

## Scenario 7: Satisfied unpublished candidate

Setup: Live evidence proves the exact requested commit exists locally with no
PR and publication is authorized.

Pass: Disposition remains `already-satisfied` while lifecycle is
`initial-publication`; no replacement implementation or commit is created.

## Scenario 8: Unstaged implementation

Setup: A unit produces an unstaged diff plus unrelated user changes.

Pass: The intended diff is reviewed, only unit paths are staged, and
`commit-message` receives that staged snapshot without touching unrelated work.

## Scenario 9: Simplify changes the candidate

Setup: A baseline passes, then simplify edits the non-trivial diff.

Pass: Earlier affected results become stale and required validation reruns on
the final candidate before commit.

## Scenario 10: Review-ready terminal state

Setup: The user requests review-ready, authorizes replies but not merge, and an
open PR needs closeout.

Pass: `pr-closeout-loop` receives review-ready as its terminal state and may
complete there rather than defaulting to merged.

## Scenario 11: Integration topology handoff

Setup: Several sources require an integration ref and promotion checkpoint.

Pass: The integration handoff carries sources, integration/protected refs,
topology and closeout authority, merge owner, and expected checkpoint.
