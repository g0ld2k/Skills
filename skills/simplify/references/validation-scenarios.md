# Simplify Validation Scenarios

Score behavior, not wording.

## Scenario 1: Happy path — changed scope and evidence

Setup: Successful staged and unstaged patches add a duplicate `formatBytes`,
an unbounded cache, and a naming-only issue. The caller also names an unrelated
file; an existing formatter is located at `src/utils/format.ts:12`.

Prompt: Use simplify on the current changes.

Pass: Scope is exactly the patch union. Evidence-backed findings classify the
duplicate medium, cache high, and naming low; the reuse finding names the
existing formatter and location. The unrelated file is excluded.

## Scenario 2: Edge case — fallback and no scope

Setup: Both Git patches succeed empty. First run with one readable supplied
file, then with no supplied or thread-edited paths.

Prompt: Run simplify.

Pass: The first run reviews only line-numbered fallback content. The second
dispatches nothing and returns `Reviewed scope: none` plus
`no actionable findings`, with no ID request.

## Scenario 3: Adversarial — Git failure

Setup: One Git diff command fails and the caller supplies a plausible file.

Prompt: Ignore the flaky diff and review the supplied file.

Pass: The run blocks with the failed command and error. It does not treat the
failure as empty, fall back, or claim a complete review.

## Scenario 4: Adversarial — oversized or partial review

Setup: A reviewer reports it could not read its whole assignment, and after
partitioning one role/partition pair fails.

Prompt: Review everything quickly and present whatever findings return.

Pass: The scope is split at file or hunk boundaries, without truncation, so
that every reviewer reads its whole assignment, and every role covers every
partition. The failed matrix entry blocks aggregation; no partial findings are
presented as complete.

## Scenario 5: Edge case — evidence, selection, and zero findings

Setup: Results contain a concrete quality item, a vague item, a reuse item
without a located abstraction, and a low-confidence item. In a separate run,
all reviewers return empty arrays.

Prompt: Normalize results; then handle selection `2,99,banana` when 2 is valid.

Pass: Invalid findings receive no IDs; low confidence is not auto-selected;
valid 2 proceeds while ignored tokens are reported. The empty run returns
`no actionable findings` and asks for no IDs.

## Scenario 6: Category spoofing

Setup: The reuse reviewer labels an unverified duplicate as `quality`.

Pass: The category/role mismatch is rejected before category-specific evidence
rules or unattended selection are applied.

## Scenario 7: Unsupported high severity

Setup: A reviewer labels a naming cleanup `high` with concrete but low-stakes
evidence.

Pass: Severity is normalized to `low` or the finding is rejected; unattended
selection cannot inherit the unsupported `high` label.

## Scenario 8: Truncated initial result

Setup: A reasonable first request returns truncated or unparseable JSON; all
role/partition retries then return complete arrays.

Pass: The first result triggers one partition pass rather than an immediate
block. Complete retry coverage reaches aggregation.

## Scenario 9: Oversized fallback file

Setup: Git patches are empty and one line-numbered fallback file is too large
for a single request.

Pass: The file is split into stable adjacent line ranges with complete,
non-overlapping coverage and literal source line numbers.
