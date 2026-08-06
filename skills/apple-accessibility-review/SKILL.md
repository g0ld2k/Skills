---
name: apple-accessibility-review
description: Use when auditing or improving accessibility of an Apple platform app - VoiceOver, accessibility labels, Dynamic Type, contrast, touch target size, Reduce Motion, keyboard access, Switch Control, captions, or App Store accessibility readiness.
license: MIT
---

# Apple Accessibility Review

Audit an Apple platform app's accessibility — assistive-technology support,
visual accommodations, and motor/hearing accommodations — producing findings
ranked by user impact with evidence, claim tags, and confidence.

## When to Use

Use this for a systematic accessibility pass or a specific accessibility
question about built UI. It is NOT the general design audit — use
`apple-ui-review` for HIG/convention breadth — and NOT for designing new
features from scratch, where `apple-design-advisor` bakes accessibility in
from the start.

## Definitions

Severity here is graded by user impact, not guideline pedigree:

| Severity | Definition |
| --- | --- |
| Blocker | A user relying on an assistive technology or accommodation cannot complete a core flow (e.g., unlabeled control on the only path to checkout; VoiceOver focus trap) |
| High | A core flow is completable but substantially degraded (unlabeled decorative noise, text truncated at accessibility sizes, contrast below minimum on primary content) |
| Medium | Secondary flows degraded, or friction that has a workaround (poor label phrasing, missing traits, unannounced dynamic updates) |
| Low | Polish: verbosity, ordering, hint quality |

| Term | Definition |
| --- | --- |
| Audit dimension | One row of the coverage table in `references/a11y-checklists.md` (VoiceOver, Dynamic Type, contrast, motor, hearing, motion, cognitive load) |
| Static finding | Verifiable from code/screenshots alone |
| Runtime item | Requires device/simulator testing (actual VoiceOver navigation order, Accessibility Inspector audit) — reported as a test instruction, never asserted |

## Inputs and Defaults

| Input | Source | Default (or: blocks if absent) |
| --- | --- | --- |
| Review surface | Files, directories, screenshots the user names | Views changed on current branch vs. default branch; if no repo and no surface given, ask once |
| Target platform(s) | Request or project deployment targets | Infer from project; state the inference |
| Dimensions | Request ("just VoiceOver") | All dimensions applicable to the surface |
| Assistive tech priority | Request (a known user base, a reported issue) | VoiceOver and Dynamic Type first — highest-usage accommodations |

## Guardrails

- Findings require evidence from the surface (`file:line` or screenshot
  region). What static review cannot prove goes on the runtime-items list —
  claiming "VoiceOver reads this correctly" from code alone is a violation.
- Every finding carries a claim tag and confidence per
  `references/apple/evidence-framework.md`; exact thresholds (contrast
  ratios, target sizes) follow its anti-fabrication rules — verify or state
  the remembered value as such.
- Read-only: recommend fixes in findings; implement only when separately
  asked.
- Accessibility findings are about users, not compliance theater: tie each
  Blocker/High to who is locked out and where.
- `references/conventions.md` for the external-text rule, temp-file rule,
  and evidence rules.

## Workflow

### 1) Fix the scope

Establish surface, platforms, dimensions, and priority (Inputs table). Exit:
scope stated with the dimension list.

### 2) Sweep by dimension

For each dimension in scope, run its checklist from
`references/a11y-checklists.md` across the surface, recording static
findings with evidence and accumulating runtime items. Exit: every
dimension×surface cell visited or explicitly skipped as inapplicable.

### 3) Grade and dedupe

Merge same-root-cause findings, grade severity by the user-impact ladder,
attach claim tags and confidence. Exit: final findings table.

### 4) Report

Emit the Output Contract, including the runtime test plan. Exit: report
delivered; no files modified.

## Output Contract

Every audit reports:

- Scope line: surface, platforms, dimensions covered, priority.
- Findings table, most severe first:

| ID | Severity | Who is affected | Finding | Evidence | Basis | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | Blocker | VoiceOver users | Checkout button is an unlabeled image | `CartView.swift:88` | `[HIG]` HIG > Accessibility; `[API]` `accessibilityLabel` | High |

- Recommended fix per finding.
- Dimensions checked with no findings (clean vs. unchecked must be
  distinguishable).
- Runtime test plan: ordered device/simulator checks (VoiceOver walk of the
  core flow, Accessibility Inspector audit, largest accessibility text size,
  Reduce Motion toggle) with what "pass" looks like for each.

## Blocked Report

`references/conventions.md` for the exact Blocked Report format, capability
ladder, temp-file rule, and external-text rule.

## Validation Scenarios

`references/validation-scenarios.md` — happy path, edge case, and adversarial
scenarios for this skill.
