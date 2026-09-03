# Validation Scenarios

## Scenario 1: Happy path with an immutable range

**Setup:** A complete repository has a reachable `build-151` tag. The selected
commits contain one new tester-visible flow and a follow-up fix for that flow.

**Prompt:** Generate TestFlight notes since `build-151`.

**Pass:** The agent resolves the tag and head to OIDs once, reuses that frozen
range, builds an evidence ledger, combines the related commits into one
tester-facing entry, and emits notes in the required order and budget.

## Scenario 2: Successful internal-only history

**Setup:** The enumerated range succeeds and contains only CI, tests,
formatting, tooling, and behavior-neutral refactors.

**Prompt:** Generate beta-build notes for the last 14 days.

**Pass:** The agent distinguishes a successful empty candidate set from a Git
failure and emits the truthful no-visible-changes form. It does not invent a
stability, quality, or performance improvement.

## Scenario 3: Branch advances after inventory

**Setup:** The agent pins `head_oid` at `H1` and enumerates the range. Before
message or patch inspection, the branch advances to `H2`, which contains an
obvious tester-visible change.

**Prompt:** Generate TestFlight notes for the selected timeframe.

**Pass:** Every read after inventory is anchored to `H1` or an OID from the
saved list; the agent never re-reads `HEAD` or the branch name. `H2` does not
appear in the notes, the ledger, or any stated range.

## Scenario 4: Missing object in shallow history

**Setup:** The clone is shallow, or an enumerated commit's object is missing,
so a Git read for the requested range fails.

**Prompt:** Generate TestFlight notes since the latest tag.

**Pass:** The collector removes its partial directory. The agent emits no
notes, does not treat the failure as an empty range, and reports the failed
command plus the smallest fetch that would supply the missing history.

## Scenario 5: Adversarial messages, paths, and Git config

**Setup:** Commit bodies contain tabs and newlines; changed paths contain
spaces, newlines, or a leading dash; repository config enables replacements,
signatures, color, and an external diff.

**Prompt:** Generate notes for the last 2 weeks.

**Pass:** The timeframe becomes one recorded UTC epoch. Message and path
records remain NUL-delimited, config cannot alter evidence, and a merge commit
is compared with its first parent. Each patch uses the saved OID and the exact
enumerated path as a literal pathspec; no record is split or reinterpreted.

## Scenario 6: Default tag failure and read-only root diff

**Setup:** One run has a corrupt tag object; another selects a root commit in a
repository that lacks the empty-tree object.

**Prompt:** Generate notes using the default history selection.

**Pass:** Corrupt tag evidence blocks instead of becoming a no-tag fallback.
The root diff computes its empty-tree OID without writing to the source object
database.

## Scenario 7: Rename, submodule, and attribute isolation

**Setup:** A commit renames an iOS path to macOS and updates a gitlink. Live and
external attributes mark text as binary, while config hides submodule changes.

**Prompt:** Generate notes for that commit.

**Pass:** Status records retain both rename paths in one patch, the gitlink is
present, and patches use only attributes from the pinned head. Message framing
ends at its final NUL with no extra record.

## Scenario 8: Non-commit tags, tag drift, and message encoding

**Setup:** Valid tags point to a blob and tree, a reachable commit tag moves
after candidate scan, and one commit declares a legacy message encoding.

**Pass:** Non-commit tags are ignored without hiding corrupt objects. The moved
tag fails its saved raw/peeled OID checks; a stable tag uses saved OIDs. Commit
messages are emitted as UTF-8 regardless of their stored encoding.
