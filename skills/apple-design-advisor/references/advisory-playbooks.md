# Advisory Playbooks

Per-mode depth for `apple-design-advisor`. Read the section for the mode
selected in Workflow step 1; skim a second section only when the request
straddles modes.

## Design Guidance

The user is deciding how something should look or behave.

Reasoning order:

1. **Find the standard pattern first.** Most design questions are "which
   existing pattern fits", not "invent a pattern". Check the component's HIG
   page (via `apple/design-domains.md`) before composing anything custom.
   Custom UI is a liability the user pays for in accessibility, adaptivity,
   and design-language churn — recommend it only when the standard pattern
   demonstrably fails the use case, and say which failure — `[REC]`.
2. **Check the pattern against every target platform** using
   `apple/platform-conventions.md`; a pattern that is idiomatic on iOS can be
   wrong on iPad width or absurd on macOS.
3. **Stress the design** against the free variables users control: Dynamic
   Type sizes, dark mode, localization lengths (German/Finnish expansion,
   right-to-left), small/large devices, offline and empty states. A design
   that only works in the happy demo state is unfinished.

Output shape: recommendation first; the pattern's name and its HIG anchor;
alternatives with the tradeoff that ruled them out; the stress-test caveats
worth designing for now.

## Implementation Assistance

The user wants code or concrete implementation direction.

- Prefer the highest-level API that satisfies the requirement (standard
  components and modifiers before custom layout, custom layout before
  drawing) — the high-level API carries accessibility, platform adaptation,
  and future design-language updates for free — `[REC]`.
- State the OS floor the code assumes; flag every availability-sensitive API
  with `[API]` and offer the fallback when the user's floor is lower.
- Follow the surrounding project's conventions (naming, state management,
  file layout) when project code is visible; idiomatic-to-Apple never
  justifies alien-to-this-codebase.
- Wire accessibility at write time (labels on symbol-only controls, Dynamic
  Type-safe text) rather than deferring it; retrofit costs more and is
  routinely skipped.
- When the request spans UIKit/AppKit and SwiftUI, recommend the seam
  explicitly (`UIHostingController`, `NSHostingView`, representables) and
  which side owns state.

Output shape: working code for the stated floor, then the notable choices
made and their tags — not a line-by-line narration.

## Architecture Discussion

The user is structuring an app, a feature, or state.

- Anchor on the platform's current data-flow model: for SwiftUI, state as
  the source of truth flowing down, actions flowing up — `@Observable`
  models, `@State` for view-local, environment for cross-cutting — `[API]`.
- Model navigation as data (paths/route values) rather than imperative
  pushes; it is what makes deep links, state restoration, and testing cheap —
  `[REC]` grounded in SwiftUI navigation APIs.
- Structure follows testability: business rules live where they can be
  exercised without rendering; view code stays thin enough that it is not
  worth testing.
- Name the boundary pattern only after the needs are on the table. Debates
  like "MVVM vs. MV" are usually proxy wars over testability and team
  familiarity — surface those directly, and mark pattern preference beyond
  the evidence as `[OPINION]`.
- Weigh architecture against the app's actual scale: solo-developer utility
  apps and 40-engineer products deserve different amounts of indirection.

Output shape: recommended structure with responsibilities per layer, the
data-flow direction, where tests attach, and what was deliberately left
simple.

## Best Practices

The user wants to know the idiomatic way, or a pre-flight check.

- Scope first: best practices for *what*, on *which platform(s)*? Turn an
  unbounded "any best practices?" into the two or three domains the user's
  actual work touches (`apple/design-domains.md`), and go deep there.
- Distinguish tiers explicitly in the answer: what Apple documents (`[HIG]`,
  `[API]`), what the platform community has settled on (`[CONV]`), and what
  is this skill's judgment (`[REC]`/`[OPINION]`). Best-practice answers are
  where tier-blurring most often happens.
- Prefer current-generation idioms and say when a practice is
  generation-sensitive (design-language changes, API migrations) so the
  answer ages visibly instead of silently.

Output shape: a short prioritized list per domain — each item tagged, with
the "why" in one clause — over an exhaustive checklist.
