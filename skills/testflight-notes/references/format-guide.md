# TestFlight Build Notes Format Guide

## Constraints

- Plain text only: no Markdown bullets or `#` headings.
- Treat 4000 characters as the repository-local default, not a claimed
  TestFlight platform limit. Draft to 3800 characters unless the caller
  supplies another budget.
- Write for people validating behavior, not engineers.

## Labels

Use one uppercase label per logical change:

- `NEW:` — a capability that did not exist before
- `IMPROVED:` — existing behavior is better or clearer
- `FIX:` — previously incorrect behavior now works as expected

Append `(iOS)` or `(macOS)` only when evidence proves that scope. Omit the
suffix when scope is shared or uncertain.

## Entry Format

Use one or two sentences and lead with the observable outcome:

```text
NEW: Timezones are now grouped into expandable buckets, making long lists easier to scan.
```

Do not expose implementation names:

```text
NEW: Added TimeZoneBucket and ManagementTimezonesTabView.
```

## Full Output

```text
What's new in this build:

NEW: <entry>

NEW (macOS): <entry>

IMPROVED: <entry>

FIX: <entry>
```

Group all `NEW` entries first, then `IMPROVED`, then `FIX`. Within a group,
place cross-platform entries before platform-specific entries. Omit empty
groups and the trailing blank line.

When the selected history succeeds but contains no supported tester-visible
change, use the truthful empty form:

```text
What's new in this build:

No tester-visible changes were identified in the selected history.
```

If over budget, remove secondary details, merge closely related improvements,
then omit the lowest-impact improvements. Preserve high-impact fixes whenever
possible; never shorten a claim until it becomes broader than its evidence.
