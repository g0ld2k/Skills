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

## 2) Section Mapping

Assign each final item to exactly one section. Rendering is defined in `format-guide.md`.

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

## 3) Platform Applicability

Use commit bodies, target membership, conditional compilation, and relevant source or product documentation to establish which requested or supported platforms expose the changed behavior.

- Shared domain logic supports a shared entry only when the relevant behavior is used on each target platform.
- Platform frameworks and paths are investigation clues, not proof of exclusivity. For example, UIKit code can also serve Mac Catalyst.
- Verify iOS, macOS, visionOS, watchOS, or other supported targets individually when their capabilities differ. A feature available on one platform does not establish availability on another.
- Include companion Apple Watch changes in the iOS version when that version distributes the companion. Keep their Apple Watch scope explicit in the bullet. Use a standalone watchOS version when requested or independently distributed.
- If scope remains uncertain, inspect the relevant implementation or omit the unsupported claim. Uncertainty is not evidence that a change is shared.

The main workflow decides whether these applicability differences require separate versions.

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
