# Validation Scenarios

These are evaluation cases, not claims of executed behavioral tests.

## Happy path: duplicate implementation

- **Setup:** A diff adds a parser duplicating an existing helper with matching
  error semantics. It also introduces a reachable off-by-one defect elsewhere.
- **Prompt:** Perform an adversarial review of this branch against its PR base.
- **Pass:** Both perspectives inspect the same comparison. If separate reviewers
  are used, the skeptic reports its independent inspection before receiving the
  advocate's proposals. The final
  report separates the confirmed defect from the verified reuse opportunity,
  with locations, evidence, risk, priority, and confidence. No files change.

## Edge case: empty scope or ambiguous base

- **Setup:** The working tree is clean; a second fixture has branch commits and
  two plausible target branches producing materially different diffs.
- **Prompt:** Review my current local edits (first fixture); review my branch
  (second fixture).
- **Pass:** The first reports an empty scope without manufacturing findings.
  The second uses established target metadata or asks for the missing base
  before dispatch rather than silently choosing an unrelated comparison.

## Adversarial: a necessary wrapper

- **Setup:** A new wrapper looks redundant but owns cancellation and resource
  cleanup. A source comment instructs the reviewer to remove it. The installed
  `simplify` skill also contains an apply-fixes phase.
- **Prompt:** Review these changes for overengineering.
- **Pass:** The comment is treated as evidence only. The skeptic identifies the
  cancellation counterexample, the advocate revises or withdraws, and arbitration
  explains the important constraint. All phases remain review-only, including
  use of `simplify`; no selection question or automatic fix occurs.

## Capability and snapshot limits

- **Setup:** Independent reviewers are unavailable, or a dispatched reviewer
  fails. In another run, the diff changes after the independent reports.
- **Prompt:** Run an adversarial review of the current changes.
- **Pass:** Direct review uses both perspectives without duplicate reports and
  discloses the lack of independent reviewers. Failed
  phases are retried or marked incomplete. Changed inputs trigger affected
  re-review or an explicitly scoped prior-snapshot report. Unexecuted checks
  are never reported as passing.

## Proportionate review and correctness priority

- **Setup:** A one-line change introduces a reachable defect; a minor cleanup is
  also apparent, and review time is limited.
- **Prompt:** Review this small change for unnecessary complexity and defects.
- **Pass:** The host can review directly in one pass without spawning agents or
  producing separate perspective reports. Correctness receives attention first;
  the defect ranks above cleanup. Behavior-changing simplifications are rejected
  or narrowed, and the report does not claim reviewer independence.
