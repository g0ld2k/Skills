# TestFlight Build Notes Format Guide

## Constraints

- Plain text only — no markdown, bullet symbols like `*` or `-`, or `#`
  headings in the clean notes block.
- Use the repository-local `MAX_NOTES_CHARACTERS` budget. Its default is 4000;
  target the smaller of that value and 3800. This is a configurable publishing
  budget, not a verified TestFlight beta-build hard limit.
- Apple currently documents a 4000-character limit for App Store metadata's
  “What’s New in this Version” field in [Platform version information](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information).
  Apple's [Beta Build Localizations](https://developer.apple.com/documentation/appstoreconnectapi/beta-build-localizations)
  documentation identifies the localized “What's New” text shown in TestFlight
  but does not state a maximum. Keep the local default clearly named rather
  than transferring the App Store field's limit to TestFlight.
- Tester audience: people validating a beta build, not engineers.

## Section Labels

Use exactly one uppercase label per logical change:

- `NEW:` — A new feature or capability that did not exist before.
- `IMPROVED:` — Existing behavior is better, faster, clearer, or more reliable
  without being a correction of previously broken behavior.
- `FIX:` — Incorrect behavior, crash, data loss, or broken interaction now works
  as expected.

## Platform Labels

Append `(macOS)` or `(iOS)` only when evidence makes the scope clear:

~~~text
NEW (macOS): A global keyboard shortcut opens the quick panel from anywhere.
~~~

Omit the platform label for shared, mixed, or unresolved evidence.

## Entry Format

Each entry is one or two short sentences and leads with the tester-visible
outcome:

~~~text
NEW: Timezones are grouped into expandable buckets, making large lists easier to scan.
~~~

Avoid internal class/type names, architecture details, and unsupported claims.

## Full Output Structure

~~~text
What's new in this build:

NEW: <entry>

IMPROVED: <entry>

FIX: <entry>
~~~

Group by `NEW`, then `IMPROVED`, then `FIX`; within a group, put
cross-platform entries before platform-specific entries. Omit empty groups and
do not add a trailing blank line.

## Output Modes

In `notes-only` mode, emit only the clean notes block above. In explicitly
requested `notes-plus-exclusions` mode, append evidence-backed exclusions:

~~~text
Excluded changes:
INTERNAL: <why the change is not tester-visible> (<sha>, <path>)
~~~

For a valid range with no retained tester-visible changes, use this clean block
instead of inventing a stability claim:

~~~text
What's new in this build:

No tester-visible changes were identified in the selected history.
~~~
