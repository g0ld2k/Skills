# Simplify Validation Scenarios

For behavioral changes, run the affected scenarios in fresh evaluation contexts
before and after the edit. Formatting-only edits need structural checks.

## Scenario 1: Severity consistency (primary)

Setup: a diff adding (a) a hand-rolled `formatBytes` duplicating an existing
util, (b) an unbounded in-memory cache, (c) a variable named `tmp2`.
Prompt: "Use the simplify skill on this diff."
Pass: (a) is medium (duplication), (b) is high (unbounded growth), (c) is low
(naming); each finding carries a confidence backed by a named file or the
absence of verification.

## Scenario 2: Proportionate review

Setup: the small diff from Scenario 1; agents are available.
Prompt: "Review this small diff; report findings only."
Pass: covers reuse, quality, and efficiency locally without forced delegation;
findings satisfy the schema, and no code changes occur without selection.

For a larger diff with independent modules, delegation is permitted when useful.
If used, reviewers receive bounded scope and relevant context, and aggregation
preserves coverage, deduplicates overlaps, and assigns sequential ids. Agent
count and exact dispatch wording are not acceptance criteria.

## Scenario 3: Selection edge

Prompt: after findings, user replies "2,99,banana".
Pass: applies finding 2 only, reports 99/banana ignored, does not re-ask.

## Scenario 4: Existing unattended selection

Setup: a diff with valid medium/high findings, a low finding, and a plausible
false positive that inspection disproves.
Prompt: "Review and fix valid in-scope medium/high findings; leave lows alone."
Pass: records the user's selection policy, reports selected ids, and applies only
covered findings without a second selection question. Selected false positives
are skipped with reasons, and affected validation follows any edits.
