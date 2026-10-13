# Release-note format preferences

Honor the requested format first. The default is plain text beginning:

```text
What's new in this build:

NEW: A new capability testers can use.

IMPROVED: An observable improvement to existing behavior.

FIX: Previously incorrect behavior now works.
```

Use one label per logical change, ordered NEW, IMPROVED, FIX. Omit empty groups.
Keep entries to one or two sentences about effects rather than internal types.
Add `(iOS)` or `(macOS)` only when platform scope is established; omitting a
suffix does not assert that an uncertain change affects every platform.

The house budget is 4,000 characters, usually aiming below 3,800. This is a
local writing preference, not a verified external platform limit. Follow a
user-supplied budget instead; preserve important fixes when shortening notes.

For a verified range with no user-visible changes, use:

```text
What's new in this build:

No user-facing changes identified in this range.
```
