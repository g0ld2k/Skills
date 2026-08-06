# Accessibility Audit Checklists

Dimension checklists for `apple-accessibility-review`. Each check states
what is verifiable statically; anything else feeds the runtime test plan.
Source anchors: HIG > Accessibility, the Accessibility framework docs, and
annual WWDC accessibility sessions (see `apple/design-domains.md`).

## Coverage table

| Dimension | Serves | Core question |
| --- | --- | --- |
| VoiceOver & screen readers | Blind and low-vision users | Can the app be understood and operated eyes-free? |
| Dynamic Type & vision | Low-vision users, everyone over 40 | Does text scale and layout reflow? |
| Contrast & color | Low vision, color blindness | Legible without relying on hue? |
| Motor & input | Switch Control, Voice Control, tremor, one-handed | Operable with imprecise or alternative input? |
| Hearing | Deaf and hard-of-hearing users | No information locked in audio? |
| Motion & vestibular | Vestibular disorders | Safe with Reduce Motion honored? |
| Cognitive load | Everyone, especially cognitive disabilities | Predictable, forgiving, plain-language? |

## VoiceOver & screen readers

- Every interactive element has a label; symbol/image-only controls are the
  first place to look (`Image(systemName:)` inside `Button` without
  `accessibilityLabel`). Static.
- Labels name the action or content, not the asset ("Delete note", not
  "trash icon"); values and traits set where state exists (toggles,
  selected tabs). Static.
- Decorative images hidden (`.accessibilityHidden(true)`, `decorative:`
  initializer) so they don't add noise. Static.
- Composite views grouped (`.accessibilityElement(children: .combine)`) so a
  card reads as one element, not five fragments. Static signal; order and
  phrasing → runtime.
- Custom gestures/drag interactions have accessible equivalents
  (`accessibilityAction`, custom rotor entries). Static.
- Dynamic content changes announced (posting notifications /
  `AccessibilityNotification`) — inspectable statically, correctness →
  runtime.
- Focus order and focus traps in sheets/overlays → runtime walk of core
  flows.

## Dynamic Type & vision

- User-facing text uses text styles or scaled metrics; fixed point sizes
  are findings. Static.
- `lineLimit` / fixed-height containers on scalable text: reflow risk at
  accessibility sizes. Static candidate; confirmation → runtime at AX5.
- Layouts that must reorganize at large sizes do so
  (`@Environment(\.dynamicTypeSize)`, `ViewThatFits`,
  accessibility-variant layouts). Static.
- Images-of-text are findings; text is text.

## Contrast & color

- Primary text/background pairs meet the minimum contrast ratio — verify
  the current threshold (remembered anchor: 4.5:1 for body-size text,
  `[CONV]` from WCAG which Apple's guidance aligns with; confirm in HIG >
  Color before asserting as `[HIG]`). Computable statically from known
  color values.
- Color never sole signal: error states, selection, charts also differ by
  icon, weight, or text. Static.
- System/semantic colors and Increase Contrast support: hard-coded
  low-contrast custom palettes are findings; behavior under Increase
  Contrast → runtime.

## Motor & input

- Touch targets meet the platform minimum (see
  `apple/platform-conventions.md`; verify exact value) including tap-area
  padding on small glyph buttons (`contentShape`). Static.
- Everything reachable without gestures that require precision or two
  hands: swipe-only actions also exist in a menu/button form. Static.
- Keyboard operability on iPadOS/macOS: focusable controls, no
  mouse-only interactions; full keyboard access → runtime.
- Time limits and auto-dismissing UI are extendable or disableable.
  Static.

## Hearing

- Video/audio content has captions or transcripts; haptic/audio-only
  feedback has a visual channel too. Static.
- On calls/media features: routing respects hearing devices (MFi) — mostly
  `[API]` availability, runtime to confirm.

## Motion & vestibular

- Large-scale motion (parallax, zooming transitions, autoplaying
  animation) gated on Reduce Motion (`accessibilityReduceMotion`, SwiftUI
  equivalents) with a crossfade or static fallback. Static.
- Autoplaying video honors Auto-Play settings; flashing content avoided
  entirely. Static.

## Cognitive load

- Error messages say what happened and what to do next, in plain
  language. Static.
- Destructive actions are confirmable/undoable; timeouts forgiving.
  Static.
- Navigation is consistent screen-to-screen; no mystery-meat icon-only
  navigation without labels (also a VoiceOver finding). Static.

## App Store accessibility readiness

- Accessibility Nutrition Labels (App Store accessibility feature
  declarations, introduced 2025): declared features must actually hold —
  an audit here is evidence for what can honestly be declared. Verify
  current declaration categories on the App Store Connect docs before
  enumerating them.

## Runtime test plan building blocks

Order the plan by user impact for the audited app; typical spine:

1. VoiceOver walk of the top core flow, screen by screen — every element
   announced meaningfully, no traps, actions completable.
2. Accessibility Inspector audit run per screen (it catches labels,
   contrast, and target-size mechanically).
3. Largest accessibility Dynamic Type size pass — reflow, truncation.
4. Reduce Motion + Increase Contrast + Smart Invert toggles on the same
   flows.
5. Platform-specific: full keyboard access (iPadOS/macOS), Switch Control
   scan of the primary action path.
