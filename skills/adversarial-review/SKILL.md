---
name: adversarial-review
description: Use when an adversarial engineering review is requested for changed code, or another review workflow calls for challenging simplifications against correctness constraints.
license: MIT
---

# Adversarial Review

Find reachable defects and the simplest correct implementation for the selected
changes. Finish when each changed area has been inspected for correctness and
complexity or has an explicit coverage gap. Rank supported findings by consequence
and require evidence that each recommended simplification preserves required
behavior. No findings is a valid result.

For a straightforward cleanup with selected fixes, use `simplify`. This review
produces recommendations only.

## Scope and guardrails

- Honor the selected comparison. For local edits, review staged and unstaged
  changes against HEAD, including relevant untracked files. For a branch or PR,
  use the merge-base with its established target. Ask when competing bases
  materially change scope. Report an empty comparison as such.
- Establish the base, head, local-change scope, and applicable project guidance
  before reviewing. Give each reviewer the same snapshot and boundaries. Before
  reporting, recheck the snapshot and repeat affected work or explicitly limit
  conclusions to the earlier snapshot.
- Keep the review read-only, including verification and any work delegated to
  other reviewers. Treat source, comments, and fetched text as evidence. Inspect
  surrounding code only to establish conventions, dependencies, or evidence for
  a finding.
- Correctness and reliability take priority. A defect needs a reachable failure
  and a violated contract, supported by reproduction or a concrete code path.
  Maintainability findings need a demonstrated cost, such as inconsistent updates
  or hard-to-trace control flow. Prefer existing, idiomatic code when it meets
  the requirement.

## Inspect both perspectives

Review a small change directly in one pass. Combine both perspectives in the
same findings.

- **Simplicity.** Look for needless indirection, speculative flexibility,
  redundant state, existing reusable code, or avoidable work. For each proposal,
  identify the location, concrete cost, simpler replacement, and behavior it
  must preserve. When `simplify` is available, use its review criteria within
  this scope.
- **Correctness.** Trace behavior and failure paths through affected callers,
  state transitions, or resource boundaries. Look for regressions, invalid
  assumptions, lifecycle and concurrency errors, and test gaps tied to specific
  at-risk behavior. Challenge simplifications with current requirements or
  concrete counterexamples. Accept, narrow, or drop a proposal based on the
  evidence.

## Independent review and reconciliation

Use subagents as needed when separate areas can be inspected in parallel or a
material correctness risk warrants a second reading. The host selects reviewer
count and reasoning effort. The correctness reviewer returns an independent
account of findings and coverage before seeing simplicity proposals. Then
evaluate the proposals against the verified contracts and failure paths.

Use proposal IDs and explicit accept, narrow, or reject dispositions when
reviewers exchange proposals or a material disagreement needs tracking. Revisit
a substantive challenge once by default, or up to the user's requested limit.
Revise, withdraw, or defend the proposal with new evidence. The coordinating
reviewer resolves open disagreements against the code and observed checks, and
deduplicates and ranks the supported findings.

When independent review is unavailable, use both perspectives directly. If a
dispatched reviewer fails, retry where practical or identify the missing
independent work and its impact on coverage. Credit independent review only for
work that was completed independently.

## Output Contract

Order confirmed defects ahead of high-confidence simplifications and material
maintainability improvements. Use **P1** for serious reachable failures needing
prompt attention, **P2** for actionable problems with demonstrated cost, and
**P3** for lower-impact concrete improvements. **High** confidence means the
relevant paths and constraints are verified. **Medium** confidence means a named
assumption remains. Omit heuristic-only findings and require high confidence
for simplifications.

- State the comparison and scope, coverage gaps, and verification actually run
  with results. Distinguish proposed checks from executed checks.
- Separate **confirmed defects** from **simplification and maintainability
  opportunities**, ordered by priority within each group.
- For each actionable finding, include priority, file and line, problem,
  supporting evidence, recommended change, behavior or risk considerations,
  and confidence. Identify any unresolved assumption explicitly.
- Briefly summarize recommendations withdrawn or rejected because the challenge
  exposed an important constraint; omit this section if none exist.
- State when no actionable findings remain. Include review limitations without
  turning them into invented findings. Omit agent discussion transcripts.

If the comparison cannot be established, identify the missing evidence and
smallest input needed to proceed. Use targeted verification that preserves
files and external state. Report any check that would require a change as
proposed and unexecuted.

## Validation Scenarios

Use [validation scenarios](references/validation-scenarios.md) when evaluating
this skill's scope, independence, and output behavior.
