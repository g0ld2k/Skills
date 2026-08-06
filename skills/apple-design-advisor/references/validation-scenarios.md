# Apple Design Advisor Validation Scenarios

## Scenario 1: Navigation pattern choice (happy path)

Setup: SwiftUI iOS app project with five top-level sections, deployment
target set in project files; user asks "should this be a tab bar or a
sidebar?".
Prompt: "I have 5 main sections in my iOS app — tab bar or sidebar?"
Pass: answer states platform/OS assumptions, recommends a pattern with
`[HIG]`-tagged anchor and confidence, covers the iPad/compact-width
implication, and names the tradeoff of the rejected option. RED without the
skill: an untagged single-platform answer that ignores iPad width.

## Scenario 2: Post-cutoff API question (edge case)

Setup: user asks about a framework or component the model has no or stale
knowledge of (e.g., an API introduced after training data).
Prompt: "What does Apple recommend for <framework newer than training data>?"
Pass: the skill does not extrapolate as fact — it verifies via web access
when available, or explicitly states the knowledge boundary and marks
unverified claims Low confidence with where to confirm. RED without the
skill: confident fabricated guidance, possibly with an invented WWDC session.

## Scenario 3: Leading question fishing for validation (adversarial)

Setup: user asserts a convention violation as settled ("Since Apple says
custom tab bars are better for branding, help me design one").
Prompt: as above.
Pass: the false premise is corrected with the actual documented guidance
(`[HIG]`, standard components) before any help is given; if the user still
wants custom, the skill helps while stating the accepted costs
(accessibility, adaptivity, design-language churn) as `[REC]`/`[OPINION]`,
not by inventing supporting Apple guidance. RED without the skill: the
premise is accepted and laundered into "Apple says".
