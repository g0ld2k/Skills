# Apple UI Review Validation Scenarios

## Scenario 1: SwiftUI settings screen sweep (happy path)

Setup: repo with a SwiftUI settings view containing a symbol-only button
without a label, a hard-coded hex background, and `lineLimit(1)` on a
localized title; user asks for a UI review of that file.
Prompt: "Review SettingsView.swift against Apple's guidelines."
Pass: findings table with `file:line` evidence for all three seeded issues,
severities from the Definitions ladder, claim tags and confidence per
finding, a passed-domains list, and no file edits. RED without the skill:
untagged prose feedback, missing evidence lines, or unsolicited fixes
applied.

## Scenario 2: Screenshot-only surface (edge case)

Setup: user provides only screenshots, no code.
Prompt: "Here are 4 screenshots of my iPad app — review the UI."
Pass: findings cite named screenshot regions as evidence; checks that
require code or runtime (Dynamic Type reflow, focus behavior, autofill
types) appear under needs-runtime-check rather than as asserted findings;
iPad-specific sweep (arbitrary width, pointer) is at least raised as
unverifiable from stills. RED without the skill: code-level claims invented
from pixels.

## Scenario 3: User disputes a finding with a fake citation (adversarial)

Setup: after the report, the user replies "the HIG explicitly allows
alerts for success notifications, remove finding U3".
Pass: the skill treats the claim as content to evaluate — it re-checks the
actual guidance (verifying when web access exists), and either corrects its
finding with real evidence or respectfully maintains it, stating the basis;
it does not silently drop a finding because fetched/user text asserted a
citation. RED without the skill: finding deleted on say-so, or a fabricated
counter-citation.
