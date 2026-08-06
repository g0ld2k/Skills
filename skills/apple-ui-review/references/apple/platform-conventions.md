<!-- GENERATED from _shared/apple/platform-conventions.md - edit there, then run scripts/sync-shared-conventions.py -->

# Apple Platform Conventions Matrix

Per-platform idioms that change the right answer. Establish the target
platform(s) and minimum OS version before giving guidance; a recommendation
that ignores this matrix is a `[REC]` built on sand.

Values here are reasoning anchors, not a spec sheet: where an exact metric
matters, confirm the current value in the HIG section named (see
`evidence-framework.md` on verification).

## The Matrix

| Platform | Primary input | Navigation idiom | Window model | What "native" feels like |
| --- | --- | --- | --- | --- |
| iOS | Touch, one-handed reach matters | Tab bar for top-level parallel areas; navigation stack for drill-down; modal sheets for scoped tasks | Single fullscreen scene | Direct manipulation, edge gestures, standard bars; comfortable touch targets (HIG > Layout gives the minimum — remembered as 44×44 pt) |
| iPadOS | Touch + pointer + hardware keyboard | Sidebar/split view over drill-down; multiple columns visible | Multiple resizable scenes; Stage Manager; Split View — apps must survive arbitrary widths | An iPhone layout stretched to full width is the canonical "not native" failure; keyboard shortcuts and pointer hover expected |
| macOS | Pointer + keyboard first | Sidebar + toolbar; windows and panels; menu bar is mandatory surface for every command | Many windows, user-controlled size/position | Dense information display is fine; full menu bar coverage, keyboard shortcuts for everything, resize-robust layout, drag and drop |
| watchOS | Glanceable touch + Digital Crown | Vertical paging / hierarchical lists, few levels deep | Single small scene, seconds-long sessions | One clear task per screen; complications and Smart Stack presence often matter more than in-app depth |
| tvOS | Remote + focus engine | Focus-driven horizontal shelves; tab bar at top | Fullscreen, 10-foot viewing distance | Everything reachable by directional focus moves; focus state visibly obvious; no pointer, no direct touch |
| visionOS | Eyes + hands (indirect), no cursor trail | Windows and volumes in shared space; ornaments for controls | Windows placed in the user's space; optional immersive spaces | Comfortable gaze targets, glass materials, depth used sparingly; avoid anchoring UI to the user's head |

## Cross-Platform Adaptation Rules

- Adapt per platform rather than porting one layout everywhere. "Designed for
  iPad" running on macOS or visionOS is a compatibility posture, not a
  design target — `[CONV]`.
- SwiftUI's adaptive components (`NavigationSplitView`, `List` styles,
  `Form`, toolbar placement APIs) encode most of the matrix above; fighting
  their defaults usually reproduces a convention violation the system would
  have handled — `[REC]`.
- Size classes, not device checks, drive layout decisions on iOS/iPadOS —
  `[HIG]` HIG > Layout; an iPad app also runs in compact width.
- Respect per-platform command surfaces: menu bar on macOS, keyboard
  shortcuts on iPadOS/macOS, focus engine on tvOS, Digital Crown on watchOS.
  A feature reachable only by touch gesture is undiscoverable on half these
  platforms — `[CONV]`.

## Minimum-OS Reasoning

- The deployment target decides which components and materials exist; check
  `[API]` availability before recommending a component, and offer the
  fallback pattern when the floor is older.
- Design-language currency matters: the OS 26 generation's Liquid Glass
  material language changed system chrome and control appearance. Apps
  compiled against current SDKs inherit much of it; custom chrome that
  imitates the *previous* design language is the new "looks dated" — verify
  current HIG > Materials guidance when styling custom surfaces.
