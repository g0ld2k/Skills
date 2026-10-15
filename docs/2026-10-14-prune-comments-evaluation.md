# Prune-comments evaluation

Tested the draft against eight disposable Git scenarios in Codex desktop using
one fresh-context subagent per arm: ordinary cleanup without the skill, the
original draft, and the revised draft. Cases ran sequentially within each arm;
they were not separate fresh-context samples. Evaluators received the requests,
fixtures, and applicable skill, but not the expected outcomes or other arms.
All edits stayed in disposable repositories; no external writes were exercised.

The agents inherited the configured model and reasoning settings. Exact model
and reasoning identifiers were not exposed by the agent tool, so they are not
recorded as known.

## Scenarios and observed decisions

| Scenario | Expected behavior | Revised result |
| --- | --- | --- |
| Explicit Python and JavaScript files | Remove trivial narration and session history; retain external constraints, API contracts, license, suppression, and deprecation annotation. | Matched. |
| Partially staged diff | Clean touched comments, including the whole partially changed block; retain untouched comments, index, unrelated edits, generated files, and vendor changes. | Matched. |
| Review only | Return findings without editing; identify ambiguous boundary behavior. | Matched. |
| No target with local changes | Inspect staged/unstaged changes and untracked source with the same boundaries. | Matched. |
| No target with clean repository | Ask for a target without expanding cleanup scope. | Matched; question recorded rather than waiting for input. |
| Adjacent arithmetic review | Review arithmetic without applying comment cleanup. | No cleanup or unsupported findings. |
| Explicit file with valuable and uncertain comments | Preserve constraint, unresolved TODO, and commented alternative without obsolescence evidence. | File unchanged. |
| Completed TODO and short test | Remove demonstrably fulfilled TODO, duplicate commented implementation, and trivial phase labels. | Matched after revision. |

The explicit-file case included a mismatch initially scored as a clear
documentation error (`double` implemented with multiplication by two, described
as tripling) and an ambiguous one (an inclusive-boundary comment above
`18 <= age < 65`). The initial revised skill removed the first and
retained/reported the second. The consistency follow-up below revisits whether
the first fixture actually established intended behavior.

The diff case changed one line of a multiline comment mixing meeting history
with a gateway constraint. Cleanup removed the history and retained the
constraint. An untouched comment beside changed executable code remained
outside the cleanup scope, even though it now disagreed with that code.

## Comparison and correction

| Arm | Automated checks passed |
| --- | --- |
| Ordinary cleanup, no specialized skill | 53/58 |
| Original draft | 57/58 |
| Revised draft | 58/58 |

These are individual assertions across the eight scenarios, not 58 independent
behavioral trials. Reports and actual patches were also read manually.

The baseline removed uncertain commented-out code and a comment that could
expose a code bug, and crossed the agreed diff boundary to delete an untouched
comment. It also removed the uncertain commented alternative in the valuable
file case. All arms preserved executable content and staging in these fixtures.

The original draft retained Arrange/Act/Assert labels in a three-statement test,
calling them useful conventional landmarks. Added a narrow navigation rule:
remove those labels in short tests with one obvious setup, call, and assertion;
conventional names alone do not establish navigation value. A fresh evaluator
then reran all eight scenarios and met every assertion.

## Verification and limits

Checked Python executable tokens and ASTs, comment-stripped JavaScript tokens,
protected text, exact index diffs, unchanged files, and expected removals or
preservations. JavaScript syntax passed using the bundled Node runtime for all
three arms. All 24 fixture repositories passed `git diff --check`. The revised
evaluator also executed the fixture's existing `test_total`, which passed.
Repository skill validation passed. The separate skill-creator validator still
could not run because PyYAML was unavailable.

This initial comparison is one sample per scenario per arm. It establishes
observed behavior on these fixtures, not consistency across repeated runs,
languages, or clients.
The adjacent request ran after the evaluator had already used the skill:
this checks task separation, not isolated live skill discovery. Required API
documentation structures, explicit overrides for generated files, and navigation
labels in large files were not separately exercised.

Raw fixtures, checker, snapshots, and evaluator reports remain outside the
working tree at `/tmp/prune-comments-eval`. The skill SHA-256 for that comparison is
`aa2fd697b36761d5315378b9530464f948627d7d3454d339b72327aab2bfbe29`.

## Independent consistency follow-up

Ran three fresh-context evaluators against the same frozen revision above.
Each received separate copies of the eight original scenarios and five new
ones: 39 scenario executions. Expected outcomes, checker, setup scripts, and
other evaluators' artifacts were withheld. The adjacent arithmetic request ran
first, with relevance decided from frontmatter before loading the skill body.
One evaluator then loaded the body for later requests before inspecting the
adjacent source; the other two completed that review before loading the body.
This improves routing isolation but still does not test live client discovery.

| New scenario | Observed in all three passes |
| --- | --- |
| Required API documentation | Preserved required JSDoc blocks, parameter/return entries, missing-value behavior, and mutation contract; removed optional redundant narrative. |
| Large-file navigation | Preserved three useful section headings across a 159-line codec module; removed 12 trivial comments and 12 session-history comments. |
| Generated/third-party override | Cleaned only the two explicitly included files; preserved marker, license, provenance, and the unrequested generated file. |
| JavaScript placement and tooling | Removed history while retaining the return line break and behavior; preserved token separation, literal comment-like text, PURE, eslint, and source-map annotations. |
| Workflow instruction | Applied cleanup when another workflow explicitly instructed it; retained useful rationale. |

All passes preserved executable content/behavior, Git indexes, unrelated work,
and review-only boundaries. Each passed 107 objective assertions. One additional
assertion, originally requiring removal of the triple-versus-double comment,
exposed a substantive judgment difference: one pass removed it and two kept it
as uncertain. Except for that choice and harmless indentation differences in
the newline-sensitive JavaScript, source results were identical across passes.

The fixture supplied no contract, test, or caller evidence to establish the
intended multiplier. Calling its comment a clear error overstated that evidence.
Clarified the skill's contradiction rule: repository evidence should establish
intended behavior; agreement between a name and implementation alone does not
settle a conflicting comment. This applies the already agreed conservative
policy rather than assuming current code is authoritative.

## Focused evidence-threshold retest

Three additional fresh-context evaluators each executed four new cases against
the clarification: 12 scenario executions. Each passed 24/24 assertions, and
manual report review confirmed the same decisions in all three passes:

| Case | Consistent result |
| --- | --- |
| Name and implementation agree, comment conflicts, no independent contract | Preserve and report ambiguity. |
| README and existing test establish twice the input | Remove the contradictory tripling comment; preserve implementation; existing test passes. |
| README and existing test establish inclusive bounds, implementation excludes upper endpoint | Preserve the valid contract comment and report the existing code defect. The deliberately failing boundary test remains failing; no code fix is authorized by comment cleanup. |
| Review-only ambiguous mismatch | Report uncertainty without recommending unconditional deletion or editing the file. |

Only the contradiction rule changed. At this stage, reused the unaffected
successful checks from the 13-case passes rather than rerunning those suites.
The subsequent full-suite run is recorded below. Focused retests cover both edits and review findings affected by the
clarification. Final skill SHA-256:
`93f5bdaec08112df108dd9e61dc36506b8f4e67d7e121fa00360911df17ffc0f`.

## Additional verification and remaining limits

The parent checker independently verified AST/token invariants, exact staging,
scope, protected text, required documentation entries, JavaScript syntax, and
runtime behavior around line breaks, token separation, and string literals.
All 39 consistency fixtures and 12 evidence fixtures passed final patch checks.
An initial checker erased a separating comment in `return/**/value`, falsely
comparing a merged token against the correctly spaced result; corrected the
checker to replace comments with whitespace. Runtime checks independently
confirmed the final behavior in every pass.

One evaluator caught and repaired an intermediate edit that flattened the
significant return line break. Others corrected trailing whitespace before
their final checks. These observations support retaining semantic verification
when comment placement matters; they do not establish error-free editing before
verification. Pytest was unavailable in some focused passes; existing fixture
test functions were invoked directly instead, including the expected failure
that demonstrates the pre-existing boundary bug.

The repeated passes use the same configured model/client and a small synthetic
suite. They establish observed agreement on these cases, not universal or
cross-model reliability. No documentation generator or live implicit skill
selection was exercised. Exact model/reasoning identifiers remain unavailable.
Raw artifacts are at `/tmp/prune-comments-consistency` and
`/tmp/prune-comments-evidence`, outside the working tree.

## Final revision: full-suite regression run

Reran all 17 accumulated scenarios in each of three newly spawned fresh-context
evaluators: 51 scenario executions against the unchanged final skill revision
`93f5bdaec08112df108dd9e61dc36506b8f4e67d7e121fa00360911df17ffc0f`.
This includes all 13 general/edge scenarios and all four evidence-threshold
cases in every pass. Restored original fixture contents and original staged
state before each run; expected outcomes and other passes were withheld.
All three completed the adjacent arithmetic review using frontmatter alone
before loading the skill body for cleanup requests.

| Independent pass | Scenarios | Parent assertions |
| --- | --- | --- |
| 1 | 17 | 132/132 passed |
| 2 | 17 | 132/132 passed |
| 3 | 17 | 132/132 passed |

The full-suite expectation for the unsupported triple-versus-double mismatch
now requires preservation, reflecting the clarified evidence rule. Existing
expectations for removal when a contract establishes the error, and preservation
when the contract instead exposes a code bug, remain intact.

Manual report and patch review confirmed agreement across all final cleanup
decisions and no observed regressions in scope, protected documentation,
generated/vendor handling, navigation, uncertainty, or executable behavior.
Original source results were byte-identical across passes in 16 of 17 cases.
The placement case differed only in indentation after the preserved return
line break; Node runtime assertions passed in every pass.

The parent independently checked Python AST/token preservation, JavaScript
syntax and placement behavior, exact index diffs, required documentation,
protected text, scope, and final patch whitespace. Existing short-test behavior
passed in every pass; the documented multiplier remained correct. The
deliberately defective inclusive-boundary fixture retained its original bug and
failing contract test, as expected: cleanup did not hide or repair that defect.
Thus passing evaluation assertions do not claim that every fixture's application
test is green.

One evaluator caught and corrected an intermediate edit that flattened the
significant JavaScript return line break; the parent checked the final corrected
file's syntax and runtime behavior. That evaluator also read committed source
during the clean-case inventory before recording the required target question;
no cleanup or edits were performed there. These are process observations, not
unreported final-output failures. The result supports the skill together with
its verification step, rather than error-free intermediate editing.

No skill changes were needed after this run. The current source still matches
the tested snapshot. Repository validation and final whitespace checks passed.
Raw fixtures, frozen skill, evaluator reports, checker, and scores are outside
the working tree at `/tmp/prune-comments-final-regression`. The model/client and
live-discovery limitations above still apply.

## PR #83: symlink source-discovery regression

Review identified an untested path boundary: an untracked `external.py` symlink
looks like source and ordinary file reads/writes follow it outside the repo.
A disposable reproduction confirmed that Git lists it as untracked source,
`Path.is_file()` follows it, and a normal comment deletion through the link
modifies the external target. Added an explicit link boundary to discovery,
explicit targets, contextual reads, and paths through symlinked directories:
report link targets without following or editing them.

Reusable scenario setup: create a disposable repository with an ordinary
`helpers.py` containing a redundant comment, and a sibling `outside` directory
containing another source file with a redundant comment. Keep initial file
bytes, link text, and index contents before requesting cleanup.

| Scenario | Setup / request | Required result |
| --- | --- | --- |
| Untracked source-looking link | `external.py` points to sibling source; default cleanup. | Report link target, preserve link and external bytes, clean ordinary changed source. |
| Staged link | Stage only the new source-looking link; default cleanup with ordinary source also changed. | Same boundary; preserve exact original index. |
| Explicit link | Name `external.py` and `helpers.py` as targets. | Explicit file selection still does not authorize following the link. |
| Linked directory | Name `linked/external.py` through a directory symlink plus ordinary source. | Detect the linked path component and preserve the external file. |

A fresh evaluator with read/write permission over the entire fixture area
completed all four cases using the skill to determine scope. It reported each
link target without reading it and removed only the ordinary source comment.
The parent checker passed 28/28 assertions: external bytes and link text
unchanged, regular cleanup performed, executable ASTs unchanged, exact index
preserved, and valid patch whitespace. Three earlier runs also passed 28/28,
but their initial repo-only access instructions duplicated the protection;
the fresh unrestricted-fixture run supplies the independent skill evidence.

All 34 repository tests, structure validation, publisher dry-run, and whitespace
checks passed. The earlier full-suite results are reused for unaffected rules;
the 17-case suite was not rerun for this targeted discovery change. Raw fixtures,
reports, and checker are at `/tmp/pr83-symlink-eval`. Tested skill SHA-256:
`936e1472918189e458f8ec06d35c259e7dbab7aa2f36831fbe21f1a7a4b17ef1`.

## PR #83: selected-version and checkout identity

Two further review comments identified distinct target boundaries. A staged new
file may have a later unstaged overlay whose comments are outside staged-only
cleanup. A requested branch/commit/PR diff may name paths that also exist with
unrelated contents in the current checkout. Clarified selected-version
eligibility, safe mapping into the working tree, and base/head identity before
editing. Cleanup must use a checkout at the selected head or report the mismatch
without editing unrelated files.

| Regression scenario | Expected behavior |
| --- | --- |
| Staged new file plus unstaged function/comment, staged-only cleanup | Remove only the index-selected comment from the working tree; preserve the overlay and exact index contents. |
| Same fixture, unstaged-only cleanup | Remove only the working-tree-diff comment; preserve the staged-only comment and exact index contents. |
| `main..feature` cleanup while initially on different `main` implementation | Resolve both refs; clean only a checkout at feature, or report the mismatch. Preserve main's implementation. |
| Same branch diff, findings only | Inspect selected-head contents through Git and report the eligible comment without edits or checkout changes. |

An initial independent evaluation preserved the overlay and branch identity but
changed the staged blob itself in the staged-only case: 18/19 parent assertions
passed. Made the existing staging-preservation requirement explicit: apply
cleanup to the working tree and leave index contents unchanged unless staging
is explicitly requested. Selecting a staged diff alone grants comment
eligibility, not permission to write the index.

A fresh evaluator reran all four original cases with the clarified skill.
All 19/19 parent assertions passed. The evaluator used an isolated feature
worktree for branch cleanup and Git object reads for review-only inspection.
The parent separately verified the feature worktree head, actual comment
removal, unchanged executable AST, and untouched feature index. The original
main checkout remained unchanged. Both local-version cases preserved their
exact original indexes and comments exclusive to the unselected version.

All 34 repository tests, structure validation, publisher dry-run, and whitespace
checks passed. Unaffected prior behavioral results were reused; the full suite
was not rerun for this targeted scope clarification. Raw artifacts are at
`/tmp/pr83-target-scope-eval` and `/tmp/pr83-target-scope-retest`. Tested skill
SHA-256: `b80199a1af52a490c81e4cfb3bc55b2833f337d58da2063cf64378d931bf204e`.

## Latest scope revision: full accumulated suite

Ran three fresh-context evaluators against commit `8166e23` and the unchanged
skill hash above. Each received fresh original fixtures for all 25 scenarios:
the original 17, four symlink cases, and four selected-version/checkout cases.
This is 75 scenario executions. Expected outcomes, original snapshots, checker,
and other passes were withheld. Fixture permissions allowed the full assigned
area, including external-target files, so permission restrictions did not
establish the symlink boundary for the evaluators.

| Pass | Parent assertions | Observed failure |
| --- | --- | --- |
| 1 | 178/179 | Multiline-comment removal collapsed a significant return line break, changing the JavaScript result. |
| 2 | 178/179 | Behavior preserved, but trailing whitespace remained in the placement fixture. |
| 3 | 179/179 | None observed. |

All selected-version, index-preservation, checkout-identity, and symlink
assertions passed in every run. All three branch-edit cases chose the skill's
permitted mismatch-report outcome rather than creating a suitable checkout;
current files and main implementations remained unchanged. Branch review used
the selected Git objects without changing checkout or files. Prior targeted
evidence for actual cleanup in a matching feature worktree remains separate.

The pass-1 failure is a real semantic change. Direct Node execution of the
original source returned `undefined` for `missing(7)`; its cleaned output
returned `7`. The evaluator used JavaScript non-comment token equality and
syntax checking, which did not detect that behavior change. Pass 2's runtime
result remained `undefined`, but the parent's `git diff --check` detected
trailing whitespace after `return`. Its reported whitespace checks covered
other Git cases rather than every edited repository. Pass 3 preserved behavior
and passed the placement patch check. The fixture's intentionally defective
age-boundary contract remains an expected failure, separate from these failures.

These outcomes do not establish consistent full-suite success. No scope-rule
failure was observed, but this sampling cannot attribute the placement failures
causally to the scope clarification. The existing general preservation rule is
not reliably producing adequate verification. A proposed follow-up is to
require parser-semantic comparison or before/after execution when line breaks
or token separation can affect behavior, and whitespace checks for every edited
file. This proposal has not been applied or tested in this run.

One evaluator directly enumerated regular external-target files while retaining
baseline fixture data, without traversing symlinks or using target contents as
comment evidence. Thus no-target-reading behavior was not universally observed;
external-target byte preservation was verified in every case. Live client
discovery, additional models/languages, and file-access tracing remain untested.

All 34 repository tests, structure validation, and publisher dry-run passed.
The skill source remains unchanged and matches the frozen suite input; failing
fixture outputs were retained without repair. Raw artifacts, reports, checker,
and assertion results are at `/tmp/prune-comments-latest-suite`.

## Verification clarification: full-suite retest

Strengthened the skill after the mixed full-suite result. For comments with
line breaks or separating tokens, require before/after parser-semantic
comparison or focused behavior execution; syntax checks and comment-stripped
token equality alone are insufficient. Preserve significant terminators and
token separation, and retain/report a placement-sensitive comment when semantic
preservation cannot be verified. Check every edited file for patch whitespace
errors, including untracked files, and correct introduced errors without
flattening significant line breaks.

Three fresh-context evaluators each ran all 25 original scenarios against the
same frozen revised skill: 75 scenario executions. Expected answers, checker,
snapshots, and other passes were withheld. Permissions covered each complete
fixture area, so access restrictions did not supply the source boundaries.
The parent reused the prior 179 assertions and added one direct whitespace
assertion that includes untracked source.

| Independent pass | Scenarios | Parent assertions |
| --- | --- | --- |
| 1 | 25 | 180/180 passed |
| 2 | 25 | 180/180 passed |
| 3 | 25 | 180/180 passed |

All three evaluators executed before/after placement checks and checked edited
file whitespace, including untracked source. The parent independently confirmed
`missing(7)` still returns undefined, `identity(7)` returns 7, and the endpoint
string is unchanged in every output. Existing scope, staging, protected text,
documentation, navigation, and symlink assertions all passed. As permitted by
the skill, all three branch-edit cases reported the checkout/head mismatch
without editing main; branch review inspected the selected objects only.

One evaluator's whitespace check caught an introduced trailing space in the
placement case, removed it, and repeated verification before completion. No
parent intervention or repair of final outputs was needed. The deliberately
defective age-boundary fixture remains an expected failure, separate from the
passing evaluation assertions. The result demonstrates consistent final
outcomes in these three runs, not error-free intermediate edits or universal
cross-model reliability.

All 34 repository tests, structure validation, publisher dry-run, and project
patch checks passed. The current skill matches the tested snapshot, SHA-256
`5b8bc65808193c46e7936304cc535dc63e03b19f4960325119a4d6d426aeeb44`.
Raw fixtures, reports, checker, and results are at
`/tmp/prune-comments-verification-suite`. No live client discovery or
documentation-generator testing was added.
