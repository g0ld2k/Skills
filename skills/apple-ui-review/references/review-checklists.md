# UI Review Checklists

Domain checklists for `apple-ui-review`. Run the domains relevant to the
review surface; skip domains the surface cannot exhibit (no forms → skip
Data entry). Each check names what to look for in code; source anchors for
the underlying guidance live in `apple/design-domains.md`.

Checks marked ⚑ are common App Review or ship-blocker territory — weigh
severity accordingly.

## Structure & navigation

- Top-level structure matches content shape: parallel peer areas → tab
  bar/sidebar; drill-down → stack; scoped task → sheet. Mixed metaphors
  (tabs that push, sheets that navigate deep) are findings.
- Navigation state is data (`NavigationStack(path:)`, route values), not
  chained booleans — weak signal alone, strong when deep links or
  restoration exist.
- Modals are dismissible and scoped; nothing essential is trapped behind an
  undismissable sheet ⚑.
- Back/cancel semantics: destructive dismissal confirms; non-destructive
  never nags.
- Search appears where the platform puts it (`.searchable`, toolbar) rather
  than as a hand-built field mid-content.

## Layout & adaptivity

- No fixed frames on text-bearing containers; layout survives long
  localizations and Dynamic Type growth.
- Size-class handling exists on iOS/iPadOS surfaces; iPad is not stretched
  iPhone. On macOS, window resize does not break layout.
- Safe areas respected; content not clipped by notch/Home indicator/rounded
  corners; `ignoresSafeArea` usage is deliberate and scoped.
- Hard-coded device checks (`UIDevice.model`, screen-size switches) are
  findings; size classes and layout APIs replace them.
- Touch targets meet the platform minimum (verify current HIG > Layout
  value; remembered as 44×44 pt on touch platforms).

## Typography & Dynamic Type

- System text styles (`.body`, `.headline`, …) or `@ScaledMetric`-scaled
  custom fonts; raw fixed point sizes on user-facing text are findings.
- Text truncation at accessibility sizes checked: `lineLimit(1)` on
  user-generated or localized strings is a candidate finding.
- Semantic hierarchy uses text styles, not manual bolding of body text.

## Color, materials & appearance

- Semantic/system colors (or asset-catalog colors with dark variants);
  hard-coded hex/RGB on system-adjacent surfaces is a finding.
- Both appearances viable: light-only assets, white-on-adaptive-background
  text, shadow-only affordances in dark mode.
- Color is never the sole carrier of meaning (also an accessibility check;
  flag and refer).
- Custom chrome imitating a previous design language's materials (flat
  blur-frosted panels where current guidance uses system materials) —
  verify against current HIG > Materials before asserting.

## SF Symbols & iconography

- Concepts with existing symbols use them; hand-drawn glyphs next to SF
  Symbols clash in weight and alignment.
- Symbol-only controls have accessibility labels (flag here, deep-dive in
  `apple-accessibility-review`).
- Symbols semantically match their meaning (`trash` deletes; `xmark`
  closes); a symbol whose per-symbol usage notes restrict it to a specific
  meaning (verify in the SF Symbols app) is not repurposed ⚑.

## Controls & feedback

- Standard control for the job: toggles for booleans, menus/pickers for
  choices, steppers for small increments; custom re-implementations of
  standard controls are findings.
- Alerts reserved for blocking situations ⚑; confirmations, undo, or inline
  status replace alert-as-notification.
- Long operations show progress and remain cancellable where possible;
  buttons show busy state rather than double-submitting.
- Destructive actions use destructive styling and are separated from
  primary actions.

## Data entry

- Keyboard type, `textContentType` (autofill), submit labels set on inputs.
- Validation is inline and specific, not an alert after submit.
- The flow asks for the minimum data, at the moment of need ⚑ (account
  requirements are App Review-sensitive).

## Empty, loading, error states

- Every list/content surface has an empty state
  (`ContentUnavailableView` or equivalent) with a next action.
- Errors state what happened and what the user can do; raw error codes or
  silent failures are findings.
- First-run works before any data exists.

## Platform-specific sweeps

Run for each target platform, from `apple/platform-conventions.md`:

- **iPadOS**: arbitrary-width survival (Split View/Stage Manager), pointer
  and keyboard-shortcut support on primary actions.
- **macOS**: every user-facing command reachable from the menu bar with
  shortcuts; toolbar customization where document-style; no iOS-ism
  imports (e.g., action sheets where a popover belongs).
- **watchOS**: per-screen scope is one task; Digital Crown scrolling not
  hijacked.
- **tvOS**: all interactive elements focusable and reachable by directional
  moves; focused state visually unmistakable ⚑.
- **visionOS**: targets sized for gaze selection; UI not head-anchored;
  depth/ornaments used per current guidance.

## Privacy & review readiness ⚑

- Permission prompts triggered in context; purpose strings explain the
  user benefit, not "app needs access".
- No dark patterns around subscriptions/ratings prompts; system rating API
  used rather than custom nag flows.
