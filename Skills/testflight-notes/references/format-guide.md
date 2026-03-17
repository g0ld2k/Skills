# TestFlight Build Notes Format Guide

## Constraints

- Plain text only — no markdown, no bullet symbols like `*` or `-`, no headers with `#`
- Total length: keep under 4000 characters (TestFlight limit)
- Tester audience: people validating features, not engineers

## Section Labels

Use exactly these uppercase labels, one per logical change:

- `NEW:` — A new feature or capability that didn't exist before
- `IMPROVED:` — An enhancement or polish to something existing
- `FIX:` — A bug fix that users would notice

## Platform Labels

When a change is macOS-only, append `(macOS)` after the label:
```
NEW (macOS): Global keyboard shortcut to open the quick panel from anywhere.
```

When a change is iOS-only, append `(iOS)` after the label:
```
FIX (iOS): Scroll position no longer resets when editing a person.
```

Omit the platform label when the change applies to both platforms.

## Entry Format

Each entry is one or two sentences. Lead with what changed, not how it was implemented.

Good:
```
NEW: Timezones Tab — Your locations are now grouped by timezone. Buckets are expandable and can be manually reordered.
```

Bad (too technical):
```
NEW: Added derived TimeZoneBucket model and ManagementTimezonesTabView with CollectionSorting-backed ordering.
```

## Full Output Structure

```
What's new in this build:

NEW: <entry>

NEW (macOS): <entry>

IMPROVED: <entry>

FIX: <entry>

FIX (macOS): <entry>
```

- Group by label type: all NEWs first, then IMPROVEDs, then FIXes
- Within each group, list macOS-specific items after cross-platform ones
- Omit empty groups entirely
- No trailing blank line
