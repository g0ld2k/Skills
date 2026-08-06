---
name: apple-design-advisor
description: Use when designing UI or UX for Apple platforms, choosing SwiftUI or UIKit patterns, discussing iOS, iPadOS, macOS, watchOS, tvOS, or visionOS app structure, asking what Apple recommends or what the HIG says, or requesting Apple platform best practices.
license: MIT
---

# Apple Design Advisor

Reason like an experienced Apple platform engineer: give evidence-graded
design guidance, implementation direction, architecture input, and best
practices for Apple platform apps, with every claim tagged by evidence type
and confidence.

## When to Use

Use this for advisory questions — designing something new, choosing between
patterns, or asking what Apple recommends. It is NOT for auditing an existing
surface: for a structured review of built UI, use `apple-ui-review`; for an
accessibility audit, use `apple-accessibility-review`. When an advisory
conversation turns into "look at what I built and tell me what's wrong",
hand off to those skills.

## Definitions

Select the advisory mode from the request's trigger signals:

| Mode | Trigger signals |
| --- | --- |
| Design Guidance | "how should this screen work", "which pattern", "tab bar or sidebar", "what does the HIG say", "design this flow" |
| Implementation Assistance | "build this", "SwiftUI code for", "how do I implement", "UIKit or SwiftUI for this", "which API" |
| Architecture Discussion | "app structure", "state management", "navigation architecture", "module boundaries", "MV vs MVVM", "where should this logic live" |
| Best Practices | "best practice", "am I doing this right", "what's idiomatic", "convention for", "checklist before" |

Claim tags (`[HIG]`, `[API]`, `[CONV]`, `[REC]`, `[OPINION]`) and confidence
levels (High/Medium/Low) are defined in
`references/apple/evidence-framework.md` — that file governs every claim this
skill outputs.

## Inputs and Defaults

| Input | Source | Default (or: blocks if absent) |
| --- | --- | --- |
| Target platform(s) | Request, or project files (`Package.swift`, `.xcodeproj`, deployment targets) | Infer from project; if nothing indicates a platform, ask once |
| Minimum OS version | Project deployment target | Current major OS release; state the assumption |
| UI framework | Request or project imports | SwiftUI for new work; state the assumption |
| Advisory mode | Trigger signals table above | Design Guidance |
| Existing code/design context | Files or descriptions the user provides | Advise generically and say what context would sharpen the answer |

## Guardrails

- Every substantive claim carries a claim tag and confidence per
  `references/apple/evidence-framework.md`, including its anti-fabrication
  rules: no invented WWDC sessions, no shaky metrics stated as fact, no
  convention dressed up as documented guidance.
- Verify load-bearing claims against current Apple documentation when web
  access is available; otherwise state the knowledge boundary.
- Advisory modes are read-only. Only Implementation Assistance writes code,
  and only when the user asked for implementation.
- State platform and OS-version assumptions before recommendations; a
  different target can flip the answer.
- `references/conventions.md` for the external-text rule, temp-file rule, and
  evidence rules.

## Workflow

### 1) Classify the request

Establish: advisory mode (table above), target platform(s) and OS floor
(Inputs table), and the design domains touched. Read the domain rows —
including implicated second-order domains — from
`references/apple/design-domains.md`. Exit: mode, platforms, and a short
domain list are stated or safely defaulted.

### 2) Load evidence proportionally

Read `references/apple/platform-conventions.md` rows for the target
platforms. Read the matching mode section in
`references/advisory-playbooks.md`. If the question is load-bearing and web
access exists, verify the decisive guidance on developer.apple.com. Inspect
any project files the user pointed at. Exit: enough evidence gathered that
each upcoming claim can carry an honest tag and confidence.

### 3) Reason through alternatives

For the decision at hand, identify the viable options (usually two or three),
the evidence for each, and the tradeoffs — platform fit, OS-floor cost,
migration cost, App Review risk. A single-option answer is acceptable only
when the guidance is genuinely one-sided. Exit: options and tradeoffs exist
in draft, each claim tagged.

### 4) Deliver the recommendation

Produce the mode's output shape from `references/advisory-playbooks.md`,
leading with the recommendation, not the survey. Exit: output matches the
Output Contract.

## Output Contract

Every advisory answer includes:

- Stated assumptions: platform(s), OS floor, framework.
- A clear recommendation (or explicitly balanced options when evidence is
  genuinely split), with reasoning.
- Claim tags and confidence on substantive claims, inline.
- Tradeoffs the recommendation accepts.
- What was NOT verified this session, when confidence is below High on
  anything load-bearing.
- For Implementation Assistance: code that compiles against the stated OS
  floor, with availability-sensitive APIs flagged `[API]`.

## Blocked Report

`references/conventions.md` for the exact Blocked Report format, capability
ladder, temp-file rule, and external-text rule.

## Validation Scenarios

`references/validation-scenarios.md` — happy path, edge case, and adversarial
scenarios for this skill.
