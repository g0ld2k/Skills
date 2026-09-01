# Immutable Git Evidence Workflow

Complete this procedure before drafting. The output is a pinned head, one
normalized selector, an exact commit set, and an evidence ledger. Reuse those
values; do not substitute live `HEAD`, a branch name, a tag name, or a freshly
parsed date later in the run.

## 1. Pin the repository and head

1. Confirm the working directory belongs to a Git repository and record its
   top-level path.
2. Resolve the current commit once as `head_oid` and require a full OID.
3. Detect a shallow repository. If history may be incomplete for the requested
   boundary, stop and report what history must be fetched. Do not interpret an
   incomplete result as an empty range.

Run evidence commands from the recorded repository root. Disable pagers,
color, signature rendering, replacement objects, external diff drivers,
text-conversion filters, and path-following behavior wherever they could alter
machine evidence. Request UTF-8 output explicitly.

## 2. Normalize the history start

Accept exactly one of these inputs:

- **Starting ref or tag:** Treat the user's text as one literal argument. If an
  unqualified name exactly matches a tag, that tag wins; otherwise resolve the
  explicit revision. Record the resolved full OID as `start_oid`, verify it is
  an ancestor of `head_oid`, and select `start_oid..head_oid`.
- **Timeframe:** Accept an ISO date or a duration of 1–3650 days or 1–520
  weeks. Parse it once to an epoch cutoff, reject overflow or an invalid date,
  and select commits reachable from `head_oid` with
  `--since-as-filter=<cutoff>`. Do not pass natural-language dates to multiple
  Git commands.
- **No input:** Resolve the latest tag reachable from `head_oid` and use its OID
  as `start_oid`. If no reachable tag exists, record a cutoff 14 days before
  inventory and use the timeframe form above.

Keep the selector as an argument array, not a reconstructed command string.
Quote every user-derived value. A missing or ambiguous revision is a blocker.

## 3. Enumerate once, then inspect that set

Enumerate full commit OIDs with the normalized selector and `head_oid`. A
nonzero Git result blocks the run. A successful result containing zero commits
is a valid empty history.

For the exact returned OIDs:

1. Read subjects and bodies with NUL-delimited fields. Tabs and newlines are
   valid commit-message content and must not become record boundaries.
2. Read name-status data with NUL-delimited paths. Preserve both source and
   destination paths for renames and copies; never split paths on whitespace.
3. Inspect merge and squash bodies. When message and path evidence do not prove
   tester effect or platform, inspect the relevant patch using the commit OID
   and literal pathspecs. Disable external diff and text conversion.

Do not rerun the selector to discover candidates. If the branch advances after
inventory, the new commit is outside this run because every read is anchored to
`head_oid` or an OID from the recorded set.

## 4. Build the evidence ledger

For every candidate note, record:

- selected commit OID or OIDs;
- relevant literal paths;
- message, path, or patch evidence for the tester-visible outcome;
- evidence for an iOS or macOS suffix, or `cross-platform/unknown`;
- included or excluded, with the classification reason.

The workflow is complete only when every selected OID was inspected without a
Git error and every drafted claim has a ledger entry. Git errors, missing
objects, ambiguous boundaries, or incomplete history emit a blocked report and
no notes.
