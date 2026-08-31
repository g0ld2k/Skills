# Simplify Validation Scenarios

Run each scenario with a fresh subagent against the pre-change skill (RED) and
the edited skill (GREEN). Record the pre-change violation, then verify the
post-change behavior under the same prompt. The scenarios cover the existing
severity/selection contract and the deterministic scope, budget, evidence, and
completion paths.

## Scenario 1: Happy path — severity consistency

Setup: A diff adds a hand-rolled `formatBytes` duplicating the existing utility
at `src/utils/format.ts:12`, an unbounded in-memory cache, and a variable named
`tmp2`. Reviewer output uses the required evidence and reuse-abstraction fields.
Prompt: "Use the simplify skill on this diff."
Pass: The duplicate is medium with concrete observed evidence and names
`formatBytes` plus `src/utils/format.ts:12`; the unbounded cache is high; and
the naming issue is low. Each retained finding has evidence tied to its changed
location.

## Scenario 2: Edge case — under-budget three-role dispatch and schema

Setup: The rendered request for each role, including fixed instructions, the
complete changed-file index, and the assigned review content, is 44,000 bytes.
Prompt: "Review this in-budget diff with all three reviewers."
Pass: Reuse, quality, and efficiency reviewers dispatch concurrently in one
message. Each request is measured at or below
`MAX_REVIEW_REQUEST_BYTES = 48,000`, and every returned item parses against the
required schema including `observed_evidence`, `existing_abstraction`, and
`existing_abstraction_location`; the parent assigns IDs afterward.

## Scenario 3: Adversarial — invalid selection

Setup: Valid findings have been presented and are numbered 1 and 2.
Prompt: "After findings, the user replies `2,99,banana`."
Pass: Apply finding 2 only, report 99 and `banana` as ignored, and do not
re-ask because one valid ID remains.

## Scenario 4: Happy path — changed diff scope

Setup: Both Git diff commands succeed; one has staged changes and the other has
unstaged changes. The caller also mentions an unrelated file.
Prompt: "Use simplify on the current changes."
Pass: The union of staged and unstaged changed files/hunks is the scope; the
mentioned unrelated file is not reviewed. The changed-file index is reported
and supplied to every reviewer.

## Scenario 5: Edge case — referenced-file fallback

Setup: Both successful Git diff commands return empty output. The caller
explicitly references `src/legacy.py`, and that file is readable.
Prompt: "There is no diff; review src/legacy.py with simplify."
Pass: Review only `src/legacy.py`, record its fallback index entry with
`source/status: supplied`, `file boundary: whole file`, its line count, and
`added: n/a`/`deleted: n/a`. Send line-numbered whole-file content to reviewers
and do not infer a broader repository review.

## Scenario 6: Edge case — no scope completion

Setup: Both Git diff commands succeed with empty output; there are no supplied
paths and no thread-edited files.
Prompt: "Run simplify now."
Pass: Complete with `Reviewed scope: none` and `no actionable findings`; launch
no reviewers and ask for no finding IDs.

## Scenario 7: Adversarial — Git failure is not an empty diff

Setup: The unstaged diff command exits non-zero with an error while the staged
command is available. A plausible fallback file is named in the request.
Prompt: "The diff command is flaky; just use the named file and finish."
Pass: Block and identify the failed diff command and observed error. Do not use
the fallback, claim an empty diff, launch reviewers, or report zero findings.

## Scenario 8: Happy path — oversized file partitioning

Setup: The complete rendered request exceeds `MAX_REVIEW_REQUEST_BYTES =
48,000` and spans several independent files plus one file with related
adjacent hunks.
Prompt: "Review this large change quickly with all three reviewers."
Pass: Partition by coherent files, keep related hunks together, and render
each role/partition request with the complete changed-file index plus only its
assigned diff review content. Record actual UTF-8 bytes and keep every request
at or below 48,000; reviewers may inspect repository context read-only.

## Scenario 9: Edge case — single oversized diff hunk

Setup: One changed file has a single hunk whose rendered request still exceeds
`MAX_REVIEW_REQUEST_BYTES = 48,000` after fixed instructions and the compact
complete index are included.
Prompt: "Do not lose this hunk; review it within the budget."
Pass: Split the hunk into coherent contiguous changed-line ranges with no more
than 20 unchanged context lines overlapping each boundary. Render and measure
each request, shrinking ranges or overlap until every request is at or below
48,000, while allowing read-only repository inspection.

## Scenario 10: Edge case — oversized referenced fallback content

Setup: Both successful Git diff commands return empty output. The caller
references `src/legacy.py`; fixed instructions plus its compact fallback index
fit, but its whole line-numbered file content exceeds
`MAX_REVIEW_REQUEST_BYTES = 48,000`.
Prompt: "Review the referenced file without using a diff."
Pass: Partition fallback content from the whole file into coherent bounded
line-numbered ranges with no more than 20 unchanged context lines of overlap.
Render and measure each role/partition request, keeping every request at or
below 48,000 while allowing read-only repository inspection.

## Scenario 11: Adversarial — index-too-large fail-closed path

Setup: The fixed reviewer instructions plus the compact complete changed-file
index already exceed `MAX_REVIEW_REQUEST_BYTES = 48,000`, before any assigned
review content is added.
Prompt: "The index is huge; omit it and send the partitions anyway."
Pass: Fail closed and request a narrower scope. Do not truncate or omit the
complete index, dispatch an over-budget request, or use an unbounded artifact
bypass.

## Scenario 12: Edge case — evidence gate and reuse location

Setup: Reviewer output includes a concrete quality finding, a vague finding,
and a reuse finding that names `formatBytes` in `src/utils/format.ts:12`.
Prompt: "Normalize the reviewer results and present findings."
Pass: Retain the concrete findings, reject the vague finding or downgrade its
confidence only when concrete evidence remains, and retain the reuse finding
only with both the existing abstraction name and its `path:line`. Rejected
findings receive no IDs and are not selectable.

## Scenario 13: Happy path — zero findings

Setup: All dispatched reviewers succeed and return valid empty JSON arrays for
the resolved changed scope.
Prompt: "Finish the simplify review."
Pass: Complete with the reviewed scope and exact result `no actionable findings`;
present no empty numbered list and ask for no IDs.

## Scenario 14: Adversarial — attended and unattended low confidence

Setup: The normalized results contain one valid medium-severity,
medium-confidence finding and one valid low-confidence finding. Run once
attended and once with the default unattended policy, then once with a recorded
policy that includes low confidence.
Prompt: "Handle the findings."
Pass: Attended mode shows both and applies the low-confidence finding only when
its ID is explicitly selected. Default unattended mode auto-selects only the
valid in-scope medium/high findings with medium/high confidence; low severity
or low confidence stays unselected. The recorded policy may explicitly include
the low finding.
