# Classification Rules for TestFlight Notes

## Goal

Translate git history into tester-facing release notes that describe observable outcomes.

## 1) Include vs Exclude

Include when testers can observe:
- New screens, tabs, flows, actions, settings, shortcuts
- Noticeable UX changes (sorting, filtering, navigation, default behavior)
- Bug fixes affecting behavior, persistence, stability, or correctness
- Platform-specific behavior differences users will notice

Exclude when primarily internal:
- CI, build scripts, linting, formatting, dependency bumps without behavior change
- Test-only changes, snapshots, fixtures, mocks
- Refactors with no user-visible impact
- Logging-only changes unless they resolve user-facing failures
- Screenshot automation and release process mechanics

## 2) Label Mapping

Use exactly one label per final item.

- NEW:
  - Capability did not exist previously
  - New surface or newly available behavior
- IMPROVED:
  - Existing behavior is better, faster, clearer, or more reliable
  - UX polish and quality upgrades that are not strict bug fixes
- FIX:
  - Incorrect behavior now works as expected
  - Crash, data loss, wrong state, or broken interaction resolved

When uncertain between IMPROVED and FIX:
- If previously broken -> FIX
- If previously worked but now better -> IMPROVED

## 3) Platform Scope Heuristics

Add `(iOS)` or `(macOS)` only with clear evidence from commit paths/messages.

Likely iOS-only signals:
- iOS-only targets/modules, UIKit-only code, iPhone/iPad specific flow notes
- File paths or target names containing `iOS`, `Mobile`, `UIKit`

Likely macOS-only signals:
- macOS-only targets/modules, AppKit-only code, menu bar/window-specific changes
- File paths or target names containing `macOS`, `Mac`, `AppKit`

Cross-platform signals:
- Shared core/domain/state logic used by both apps
- Notes or PR body explicitly say both platforms

If evidence is mixed or unclear, keep cross-platform (no suffix).

## 4) Deduplication Rules

Treat these as one final note:
- Initial feature + 1-3 follow-up fixes in same user journey
- Rename/reword commits describing same behavior outcome
- Parallel commits touching multiple files for same visible change

Do not merge unrelated fixes just because they share a label.

## 5) Wording Rules

Prefer:
- Observable outcomes: "Editing no longer resets scroll position"
- Simple nouns and verbs testers understand
- One or two short sentences

Avoid:
- Internal class/type names
- Architecture details
- "Refactored", "migrated", "restructured", unless tied to user benefit

## 6) Confidence Rules

Only emit a note when confidence is high.
If confidence is low:
- Keep it broad and safe, or
- Omit it

Prefer missing a minor improvement over including an inaccurate claim.
