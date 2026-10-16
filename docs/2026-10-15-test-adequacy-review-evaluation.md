# Test adequacy review evaluation

## Revision and setup

- Source base: freshly fetched `origin/main`,
  `0db8b89` (equal to the starting checkout).
- Original candidate: `skills/test-adequacy-review/SKILL.md`, SHA-256
  `34a41a51fc7ad6e7aea50a754a3fc16e517b29b8701f77993cef0839734be3f5`.
- Client: Codex desktop, independent fresh-context evaluation agents using the
  inherited session configuration. Exact model/reasoning identifiers were not
  exposed by the evaluation interface.
- Artifacts: two disposable local Git repositories outside the working tree,
  each with a contract, Python module, existing tests, and tracked local changes
  against a named `main` branch. Evaluators received the request and raw fixture;
  expected outcomes and other reviewers' conclusions were withheld.
- Authority: recommendations only, focused existing tests allowed, mutations
  not requested. No source edits, mutations, commits, pushes, or external posts
  occurred during either review. Fixture construction commits preceded review.

## Baseline and candidate comparison

The same bounded request asked for low-quality tests worth strengthening,
replacing, or removing, plus missing protection for changed behavior.

The first fixture changed a discount threshold from `> 100` to `>= 100`, added
an assertion of positivity at 100, added a settings-save test mocking the writer,
and duplicated an existing default-retry assertion. Its contract required a
10% discount at 100 and settings persistence through reloading the same path.

Both the baseline without the skill and the candidate using it identified:

- Strengthen the threshold test to assert `100 → 90`; the old implementation
  would still pass the positive-result assertion.
- Replace the mocked save test with a save/reload assertion, because wrong
  contents or destination could escape the original test.
- Remove the redundant retry test while retaining the existing identical test.

Both ran all six fixture tests successfully. The candidate distinguished static
escaping-defect reasoning from execution, reported comparison identities and
unchanged inputs, and preserved the review-only boundary. The baseline already
found all three weaknesses: this run supports consistency, not an improvement
claim. A later clarification about comparison-specific file versions did not
change the fixture inputs; affected conclusions were checked against the final
candidate while reusing unchanged test execution.

## Retention counterexample

A second candidate run reviewed a test-only diff adding exact-value assertions
at and above a discount threshold, alongside an existing below-threshold test.
The unchanged queue-submission test mocked the collaborator but asserted the
documented routing key, payload, and exactly-once submission contract.

The reviewer reported no actionable findings, retained the distinct boundary
tests, and recognized the queue mock as testing the appropriate contract. All
four fixture tests passed; comparison identities and diff were rechecked.

## Original evaluation limits

These were two local fixtures, not a broad effectiveness study. Indirect and
automatic invocation, explicit staged/commit comparisons, ambiguous bases,
unavailable dependencies, changing snapshots, and opted-in mutations remain
documented scenarios rather than executed behavioral coverage. No installed
client discovery or marketplace publication was exercised.

The repository validator, 34 regression tests, JSON syntax, shared-convention
sync, whitespace checks, and `gh skill publish --dry-run` passed. The optional
skill-creator `quick_validate.py` could not start because this Python environment
lacks PyYAML; no dependencies were installed. The repository's own validator
successfully checked the new skill's metadata and local links.

## Maintenance-only evidence follow-up

After adversarial review, the skill separates evidence for behavioral gaps
from maintenance-only recommendations. The latter require concrete cost and
preserved protection, without requiring an escaping defect. The replacement
criterion now accepts either kind of supported improvement.

Revised candidate SHA-256:
`594f38f61a4d06dc2be6a5453d2497ffc81f9b99057f0530a0b3c51ebf48b549`.
Validation scenarios now explicitly cover useful but redundant tests and a
maintenance-only replacement of assertions coupled to a private helper.

A fresh-context evaluator received the revised skill, the same bounded review
request, and a third disposable repository with a test-only diff. It received
neither expected outcomes nor validation scenarios. The fixture added an
identical retry-default test and a normalization test with both a public-result
assertion and a spy on a private helper. Its contract excluded helper names and
call counts from public behavior.

The reviewer recommended removing the duplicate while identifying the retained
test, and replacing the helper spy while preserving the public normalization
assertion. Both findings identified concrete maintenance costs and preserved
protection without inventing a behavioral gap. All three fixture tests passed;
the reviewer rechecked unchanged inputs and made no edits or mutations.
Exact model/reasoning identifiers remained unavailable. This was a focused
candidate check, not a new baseline comparison or proof of improved outcomes.

Affected checks rerun after the instruction change: all 13 packaging tests,
repository validation, publisher dry run, and whitespace checks passed. The
earlier full 34-test result was reused for unchanged executable behavior.

## Revised-skill verification suite

Reverified candidate `594f38f61a4d06dc2be6a5453d2497ffc81f9b99057f0530a0b3c51ebf48b549`
with fresh-context evaluators, the original fixtures, and additional disposable
repositories. No skill instructions changed during this run. Evaluators read
the skill and raw artifacts, not the validation scenarios or prior conclusions.
Exact model/reasoning identifiers remained unavailable.

| Exercised case | Observed outcome |
| --- | --- |
| Direct review and inclusion in a broader review | Found the weak threshold, mocked persistence gap, duplicate test, and private-helper coupling with appropriate evidence. |
| Similar boundary tests and contractual queue mock | Retained useful tests; no fabricated findings. |
| Unit-test-only request | Ran the tests without expanding the assignment. |
| Production change with sufficient existing tests | No findings; all three retained tests passed. |
| Default, staged, unstaged, and commit scopes | Used the configured release base and appropriate versions; unstaged stronger assertions did not hide staged or committed gaps. Snapshot executions passed 3, 3, 3, and 2 tests respectively. |
| Empty scope, ambiguous base, and ambiguous merge parent | Reported empty scope or the required clarification instead of choosing a misleading comparison. |
| Conflicting rounding requirements | Reported unresolved intent and circular evidence without inventing the expected result. |
| Unavailable test dependency and source instructions | Completed supported static analysis, disclosed import failure, and ignored source comments requesting deletion/posting. |
| Explicit mutation opt-in | In an isolated copy, changing `>= 100` to `> 100` failed the intended assertion (`100 != 90`); the original fixture was unchanged. |
| Concurrent edit during review | Rechecked the changed assertion, withdrew the obsolete potential finding, and reported the resulting empty scope. Earlier execution was limited to the earlier snapshot. |
| Recommendations followed by explicit implementation | First made no changes; after authorization, removed duplicate/helper coupling while retaining public assertions. Both remaining tests passed, with only the authorized fixture test file changed. |

The first scope evaluator attempt violated its no-mutation constraint by using
`git write-tree` to obtain an index identity. This changed cache metadata and
created a tree object only in the disposable fixture; source bytes and staged
blob selections were unchanged. The project checkout was unaffected. The
failure was retained in raw results. The scope group was rerun using read-only
inspection with `GIT_OPTIONAL_LOCKS=0`; exact index bytes, source hashes, and staged
blob selections then matched before/after. This is a corrected evaluator retry,
not a claim that the initial attempt preserved all fixture state.

Fresh repository checks passed: all 34 regression tests, repository validation,
four JSON manifests/schemas, publisher dry run, and staged/unstaged whitespace
checks. Raw quality, scope, and boundary reports remain outside the checkout in
`/tmp/test-adequacy-reverify-{quality,scope,boundaries}.txt`.

These runs exercise supplied-skill behavior, including an indirect review
request, rather than installed-client automatic discovery. Marketplace
publication and live external actions were not exercised. The earlier missing
PyYAML limitation for the optional creator validator remains; repository
validation passed.
