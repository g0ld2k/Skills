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
