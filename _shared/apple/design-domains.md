# Apple Design Domain Index

Route evidence-loading through this table: identify which domains a request
touches, then read only those rows and the sources they point at. Load the
whole file's worth of sources for no request.

| Domain | Key questions | Where authoritative guidance lives |
| --- | --- | --- |
| App structure & navigation | Flat (tabs) vs. hierarchical (stack) vs. sidebar? Modal vs. push? Where does search live? | HIG > Navigation and search, Tab bars, Sidebars, Sheets; WWDC sessions on SwiftUI navigation; `NavigationStack`/`NavigationSplitView` docs |
| Layout & adaptivity | Does it survive every size class, window size, Dynamic Type size, and orientation? Safe areas respected? | HIG > Layout; size-class and `ViewThatFits`/grid API docs; WWDC sessions on adaptive layout |
| Typography & Dynamic Type | System text styles used? Does layout reflow at accessibility sizes? Custom fonts scaled? | HIG > Typography; `Font.TextStyle`, `@ScaledMetric` docs |
| Color & materials | System/semantic colors first? Legible in light, dark, and increased-contrast? Materials vs. flat fills per current design language? | HIG > Color, Dark Mode, Materials; asset-catalog color docs |
| SF Symbols & iconography | Symbol exists for the concept? Correct weight/scale pairing with text? Rendering mode (monochrome/hierarchical/palette/multicolor) chosen deliberately? Restricted-use symbols avoided? | SF Symbols app + HIG > SF Symbols; symbol rendering WWDC sessions; per-symbol usage notes in the SF Symbols app |
| Controls & inputs | Standard control that already does this? Correct control for the value type? Platform-appropriate (menu vs. picker vs. segmented)? | HIG per-component pages (Buttons, Pickers, Menus, Toggles, …); SwiftUI/UIKit/AppKit control docs |
| Feedback: haptics, sound, alerts | Alert only for genuinely blocking situations? Haptics semantic (`sensoryFeedback`/`UIFeedbackGenerator`) and sparing? Progress communicated for long work? | HIG > Feedback, Alerts, Playing haptics; framework docs |
| Motion & animation | Purposeful (orientation, causality) vs. decorative? Honors Reduce Motion? Uses system springs/durations? | HIG > Motion; SwiftUI animation docs; WWDC animation sessions |
| Data entry & forms | Right keyboard type, text content type (autofill), input accessories? Validation inline and forgiving? Least data asked latest? | HIG > Entering data; `textContentType` docs; App Review Guidelines on account requirements |
| Empty states, onboarding, errors | First-run teaches by doing rather than tutorial walls? Empty states actionable (`ContentUnavailableView`)? Errors say what happened and what to do? | HIG > Onboarding, Launching; `ContentUnavailableView` docs |
| Accessibility | See `apple-accessibility-review` skill for the audit workflow; advisory rule: accessibility is a design input, not a retrofit | HIG > Accessibility; Accessibility framework docs; annual WWDC accessibility sessions |
| System integration | Should this surface as a widget, Live Activity, App Intent/Siri, Spotlight, share extension, notification? Interruption level appropriate? | HIG > Widgets, Live Activities, App Shortcuts, Managing notifications; WidgetKit/App Intents docs |
| Privacy & App Review | Permission requested in context with a purpose string that says why? Sign in with Apple obligations? Data-collection disclosures (privacy nutrition label) accurate? | App Review Guidelines; HIG > Privacy; privacy manifest docs |
| App architecture (engineering) | State ownership (`@Observable`/`@State`/environment)? Navigation state modeled as data? Dependency boundaries testable? UIKit/AppKit interop seams clean? | Framework docs and WWDC sessions on SwiftUI data flow; sample apps (e.g., Apple's tutorial and sample-code catalog) |

## Domain-Selection Heuristics

- A request usually names one domain but *implicates* two or three: a
  navigation question implicates layout (split-view widths) and architecture
  (navigation state as data). Read the implicated rows too; the second-order
  domains are where inexperienced designs fail — `[REC]`.
- When a request spans four or more domains, that is a full review, not a
  question: switch to `apple-ui-review` or `apple-accessibility-review`
  posture rather than answering domain-by-domain.
- "What does Apple recommend for X" with an X absent from this table is the
  cue to search current Apple documentation rather than extrapolate — new
  frameworks earn rows here over time, and absence usually means post-cutoff
  or niche, both of which demand verification.
