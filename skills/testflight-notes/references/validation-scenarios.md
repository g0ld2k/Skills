# Validation Scenarios

## Scenario 1: Happy path with an immutable range

**Setup:** A complete repository has a reachable `build-151` tag. The selected
commits contain one new tester-visible flow and a follow-up fix for that flow.

**Prompt:** Generate TestFlight notes since `build-151`.

**Pass:** The agent resolves the tag and head to OIDs once, reuses that frozen
range, builds an evidence ledger, combines the related commits into one
tester-facing entry, and emits notes in the required order and budget.

## Scenario 2: Successful internal-only history

**Setup:** The normalized range succeeds and contains only CI, tests,
formatting, tooling, and behavior-neutral refactors.

**Prompt:** Generate beta-build notes for the last 14 days.

**Pass:** The agent distinguishes a successful empty candidate set from a Git
failure and emits the truthful no-visible-changes form. It does not invent a
stability, quality, or performance improvement.

## Scenario 3: Adversarial drift and evidence failure

**Setup:** Inventory pins `H1`; the branch advances to `H2` before patch
inspection. Selected commits include multiline messages and paths containing
spaces, tabs, or glob characters, while local Git configuration enables
transformed output. A required object is then missing from the shallow clone.

**Prompt:** Generate TestFlight notes for the selected timeframe.

**Pass:** Every attempted read remains anchored to `H1` or its recorded commit
set; NUL-delimited records and literal pathspecs preserve the available
evidence, transformations are disabled, and `H2` is excluded. On the missing
object, the agent emits no notes and reports the smallest fetch needed to
continue instead of treating the failure as empty history.
