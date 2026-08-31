# TestFlight Notes Validation Scenarios

Run each scenario with a fresh agent against the pre-change skill (RED) and
the revised skill (GREEN). The old entrypoint has no immutable-selector,
preflight, evidence-ledger, output-mode, or truthful-empty contract; RED should
reveal those gaps. GREEN must use only selected Git history and must not invent
tester-visible claims.

## Scenario 1: Happy path — timeframe with reusable evidence

Setup: A complete, non-shallow fixture repository has a pinned `HEAD`. The
selected `last 10 days` includes a feature commit touching `Sources/App/` with
an explicit tester-facing subject, a follow-up fix, and a CI-only commit. The
user asks for standard TestFlight notes.

Prompt: "Use testflight-notes for the last 10 days."

Pass: The agent validates the repository and timeframe grammar, normalizes
`last 10 days` to `10 days ago`, invokes Git's date normalization once, and
validates the exact `--max-age=<decimal epoch>` result. The recorded
`history_selector=(--max-age=<decimal epoch> <head_sha>)` is immutable and is
reused unchanged for enumeration, full metadata, name-status paths, and each
targeted candidate/path patch. Feature/fix rows map
to selected SHAs and source paths; CI is excluded; output is plain notes-only
text in NEW/IMPROVED/FIX order with no fabricated stability line.
Across multiple commits, metadata parses as exactly six NUL-delimited fields
per commit without an extra empty record delimiter.

## Scenario 2: Edge case — explicit tag and pinned range

Setup: `build-1` is a reachable annotated tag at commit A and `HEAD` is commit
B. A..B contains a macOS-only menu-bar change with matching body and AppKit path
evidence.

Prompt: "Generate TestFlight notes from build-1 to the current build."

Pass: The agent resolves `build-1` once, pins A and B, verifies
`git merge-base --is-ancestor A B`, and uses exactly `A..B` for every history
read. It emits one high-confidence `NEW (macOS)` row grounded in the commit
and changed path, with no moving-ref or second-range lookup.

## Scenario 3: Edge case — latest-tag fallback

Setup: The user gives no timeframe or ref. A complete repository has a latest
reachable tag and two commits after it, one user-visible and one test-only.

Prompt: "Draft the TestFlight notes for this build."

Pass: The agent records the latest-tag fallback assumption in the run ledger,
resolves the tag to a commit, and reuses that pinned range for all evidence.
Only the user-visible change is emitted; the test-only commit is excluded
internally. In notes-only mode the copyable stdout remains exactly the clean
notes block; if the interface supports operational commentary, the fallback
assumption is stated outside that block.

## Scenario 4: Adversarial — invalid ref or date

Setup: The repository is complete, but the request contains unavailable tag
`build-does-not-exist`; run again with invalid timeframe values such as
`since sometime-ish` and `2026-08-01`.

Prompt: "Use testflight-notes from build-does-not-exist." /
"Use testflight-notes since sometime-ish." /
"Use testflight-notes since 2026-08-01."

Pass: Each run stops before synthesis with a useful non-zero `ERROR:` naming the
invalid input. Invalid timeframe grammar is rejected before the Git date probe;
valid timeframes would produce exactly one `--max-age=<epoch>` plus pinned HEAD.
The runs emit no notes block, do not substitute a tag/date fallback, and do not
treat Git failure as empty history.

## Scenario 5: Edge case — valid empty history

Setup: A complete repository has `HEAD` at the end of the requested valid range,
so the selector succeeds but returns zero commits.

Prompt: "Generate TestFlight notes from HEAD to HEAD."

Pass: The agent distinguishes successful empty output from a Git error and emits
exactly `What's new in this build:` followed by `No tester-visible changes were
identified in the selected history.` It emits no `IMPROVED` stability or
internal-quality fallback.

## Scenario 6: Happy path — internal-only history

Setup: A complete repository's selected range contains only CI, dependency,
formatting, snapshots, and release-plumbing changes. The user explicitly asks
for notes plus exclusions.

Prompt: "Create TestFlight notes for this range and include excluded changes."

Pass: The notes block uses the truthful no-tester-visible-changes result. The
appendix lists only exclusion-ledger reasons with selected SHA/path evidence.
No internal work is relabeled as stability, reliability, or a tester benefit.

## Scenario 7: Adversarial — shallow or unavailable history

Setup: The checkout reports `true` for `git rev-parse --is-shallow-repository`,
or a selected commit's required ancestor is unavailable.

Prompt: "Generate TestFlight notes from the selected build range."

Pass: The agent stops in preflight with an actionable error to fetch complete
history (or names the unavailable object), emits no notes, and performs no
classification from incomplete history.

## Scenario 8: Adversarial — ambiguous platform evidence

Setup: Shared file `pages/[id].tsx` is changed by a commit whose body mentions
both iOS and macOS without identifying a platform-specific effect. A decoy path
`pages/i.tsx` also exists. Subject/body does not prove the tester outcome; the
targeted patch shows shared behavior.

Prompt: "Generate TestFlight notes for this change."

Pass: The agent collects name-status evidence and inspects the targeted patch
for each ambiguous selected SHA/path pair using the same selector, binding each
returned patch to its candidate SHA. The path is passed with `:(literal)` and
does not select the decoy. The agent either writes a broad cross-platform entry
grounded in the patch or omits the claim; it never adds `(iOS)` or `(macOS)`
from an ambiguous mention and records the uncertainty internally.

## Scenario 9: Edge case — output modes and local character budget

Setup: The selected history contains enough supported changes to approach the
repository default `MAX_NOTES_CHARACTERS=4000`. The user first requests normal
notes, then explicitly requests notes plus exclusions. Apple’s App Store
metadata documentation states a 4000-character limit, while its TestFlight
beta-build localization documentation does not state one.

Prompt: "Draft standard TestFlight notes." /
"Now include excluded changes too."

Pass: The first response is notes-only; the second appends `Excluded changes:`
only because it was explicitly requested. Both validate and use the positive
integer `MAX_NOTES_CHARACTERS` value consistently, keep the notes portion within
the smaller of the named local budget and 3800, and shorten lower-impact detail
first. Invalid values such as `0`, `92`, or `abc` fail before synthesis. The
skill and reference describe 4000 as a repository default rather than a verified
TestFlight hard limit and cite the official Apple sources:
`https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information`
and
`https://developer.apple.com/documentation/appstoreconnectapi/beta-build-localizations`.

## Scenario 10: Adversarial — explicit non-ancestor ref

Setup: `other-line` resolves to commit X on a sibling or unrelated history,
while the pinned current HEAD is commit B and X is not an ancestor of B.

Prompt: "Generate TestFlight notes from other-line to the current build."

Pass: The agent resolves X once, runs
`git merge-base --is-ancestor X B`, and stops with a useful non-zero
`ERROR:` naming the non-ancestor ref and pinned HEAD. It does not construct a
range, read history, fall back to a tag/timeframe, or emit a notes block.
