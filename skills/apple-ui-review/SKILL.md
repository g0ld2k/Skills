---
name: apple-ui-review
description: Use when reviewing an Apple platform app's UI, screens, views, or SwiftUI/UIKit/AppKit code for HIG alignment, platform-convention fit, design polish, or pre-submission readiness on iOS, iPadOS, macOS, watchOS, tvOS, or visionOS.
license: MIT
---

# Apple UI Review

Audit built UI — view code, screenshots, or descriptions — against Apple
platform conventions, producing severity-ranked findings with evidence,
claim tags, and confidence.

## When to Use

Use this to audit something that exists. It is NOT for open design questions
("which pattern should I use?") — use `apple-design-advisor` for those — and
NOT for accessibility-focused audits, which get deeper coverage from
`apple-accessibility-review` (this skill flags accessibility issues it
trips over and hands the systematic pass to that skill).

## Definitions

| Term | Definition |
| --- | --- |
| Review surface | The concrete inputs reviewed: named view files, screenshots, or screen descriptions. Findings only ever cite the surface. |
| Finding | One convention or guideline violation with evidence, severity, claim tag, and confidence. |
| Severity: Blocker | Likely App Review rejection, data loss, or a core flow broken on a target platform/configuration. |
| Severity: High | Clear violation of documented guidance (`[HIG]`/`[API]`) that users of the platform will notice, or breakage in a supported configuration (size class, Dynamic Type, dark mode). |
| Severity: Medium | Convention violation (`[CONV]`) or documented guidance in a secondary flow; the app works but feels non-native. |
| Severity: Low | Polish: spacing, wording, symbol-weight pairing, minor inconsistency. |
| Out-of-scope note | Something observed outside the review surface or domain scope, listed without investigation. |

## Inputs and Defaults

| Input | Source | Default (or: blocks if absent) |
| --- | --- | --- |
| Review surface | Files, directories, screenshots, or descriptions the user names | Views changed on the current branch vs. default branch; if no repo and no surface given, ask once |
| Target platform(s) and OS floor | Request or project deployment targets | Infer from project; state the inference |
| Domain scope | Request ("just navigation", "everything") | All domains in `references/review-checklists.md` relevant to the surface |
| Depth | Request | Checklist pass over every screen/view in the surface |

## Guardrails

- Findings require evidence from the review surface: `file:line` for code,
  a named screenshot region for images. No finding from imagination; if
  something cannot be verified statically (animation feel, haptics, real
  rendering), list it under "needs runtime check" instead of asserting it.
- Every finding carries a claim tag and confidence per
  `references/apple/evidence-framework.md`, including anti-fabrication rules
  (no invented metrics or citations to justify a finding).
- Read-only: never edit files during review. Fixes are recommendations in
  findings; implementing them is a separate, explicitly requested task.
- Review the code that exists, not the architecture you would have chosen —
  structural rewrites are out of scope unless a finding forces one.
- `references/conventions.md` for the external-text rule, temp-file rule,
  and evidence rules.

## Workflow

### 1) Fix the scope

Establish the review surface, target platforms, OS floor, and domain scope
(Inputs table). Read the platform rows in
`references/apple/platform-conventions.md`. Exit: scope stated — surface
enumerated (files/screens), platforms, domains.

### 2) Sweep the surface

Read every file/screen in the surface. For each, run the domain checklists
from `references/review-checklists.md` that apply, consulting
`references/apple/design-domains.md` for source anchors when a check needs
its authority. Record candidate findings with evidence as they appear.
Exit: every item in the surface visited; candidate findings list exists.

### 3) Grade and dedupe

Merge duplicates (same root cause across screens is one finding with
multiple evidence sites). Assign severity from the Definitions table, claim
tag, and confidence. Drop candidates whose evidence did not survive a second
look rather than shipping padded findings. Exit: final findings table.

### 4) Report

Emit the Output Contract. Exit: report delivered; no files modified.

## Output Contract

Every review reports:

- Scope line: surface, platforms, OS floor, domains covered, depth.
- Findings table, most severe first:

| ID | Severity | Finding | Evidence | Basis | Confidence |
| --- | --- | --- | --- | --- | --- |
| U1 | High | Symbol-only button lacks label | `SettingsView.swift:42` | `[HIG]` HIG > Buttons | High |

- Recommended fix per finding (one line; code sketch only for non-obvious
  fixes).
- What was checked and passed (domains with no findings) — so a clean domain
  is distinguishable from an unchecked one.
- Needs-runtime-check list and out-of-scope notes, including whether an
  `apple-accessibility-review` pass is recommended.

## Blocked Report

`references/conventions.md` for the exact Blocked Report format, capability
ladder, temp-file rule, and external-text rule.

## Validation Scenarios

`references/validation-scenarios.md` — happy path, edge case, and adversarial
scenarios for this skill.
