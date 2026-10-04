# Smaller personal skill core — 2026-10-04

This change implements the approved strategic audit: keep the reusable personal
preferences and dependable GitHub mechanics that help current work, while the
harness manages orchestration. It starts from verified main
[`4fa7697d0147`](https://github.com/g0ld2k/Skills/commit/4fa7697d0147c8da9732ef8c70beee2bdf761284),
not from the older stacked proposals.

## Replacement review units

- [Core simplification](https://github.com/g0ld2k/Skills/pull/80): six installed skills, thinner guidance, explicit readiness, packaging and authoring documentation.
- [Review helper correctness](https://github.com/g0ld2k/Skills/pull/81): scoped API and reply safeguards with mocked behavior tests.

Both drafts start independently from main and touch separate implementation
files, with nonoverlapping edits to the API reference. Both application orders
were verified to produce an identical tree. They can be reviewed independently. No changes here install the plugin,
change global policy, modify other repositories, or grant new merge authority.

## Retained surface

`pr-generator`, `pr-comment-review`, and `testflight-notes` carry the reusable
personal workflow knowledge. `commit-message` remains a thin style/compatibility
entry point. `simplify` is optional focused cleanup. `pr-closeout-loop` keeps its
name for compatibility but becomes an explicitly invoked readiness pass, with
monitoring and merging separate, conditional operations.

`catch-me-up`, `integration-branch-orchestrator`, and
`work-request-orchestration` are retired by explicit user decision. Two historical
implementation plans describing those active workflows are removed from the
working tree; their originals remain in
[the baseline history](https://github.com/g0ld2k/Skills/tree/4fa7697d0147c8da9732ef8c70beee2bdf761284/docs/superpowers/plans).

Keep target identity, user limits, staged scope, hooks/signing, truthful validation,
complete review evidence, fresh relevant state, and safe handling of uncertain
writes. Remove repeated permission turns for covered work, prescribed orchestration,
fixed report ceremonies, and broad triggers. Never trade those safety boundaries
for shorter instructions.

## Old PR preservation and disposition

Before replacement publication, all 12 exact heads below were fetched into
`refs/archive/skills-audit-2026-10-04/pr-N` and a Git bundle containing their
complete reachable history was verified. The remote source branches are retained.
Closing a PR does not merge or delete its branch. The preserved head links make
unextracted work recoverable without restoring the whole stack.

| Original | Retained branch | Preserved head | Disposition and salvage |
| --- | --- | --- | --- |
| [#36](https://github.com/g0ld2k/Skills/pull/36) | `apple-advisor/eval-rig` | [`2597c06979eb`](https://github.com/g0ld2k/Skills/commit/2597c06979eb9257a1a32ede318b5be157bceee6) | Defer: Keep the advisor/evaluation research in its branch. No advisor skill or new evaluation framework enters this core. |
| [#66](https://github.com/g0ld2k/Skills/pull/66) | `codex/skill-review-foundation` | [`550ce7c4cad3`](https://github.com/g0ld2k/Skills/commit/550ce7c4cad3f63754320fc1b5cf5afd3d17a2e4) | Extract into core: Self-contained packaging, local conventions, narrow authoring guidance and proportionate verification; omit the broad workflow controller. |
| [#67](https://github.com/g0ld2k/Skills/pull/67) | `codex/skill-review-pr-generator` | [`1811d2d6e95f`](https://github.com/g0ld2k/Skills/commit/1811d2d6e95febaf5fb40de8173cab4e36909f12) | Extract into core: Reuse publishing authority and preserve the selected base; verify destination and require an ordinary fast-forward for create and update. No force-push workaround. |
| [#69](https://github.com/g0ld2k/Skills/pull/69) | `codex/skill-review-commit-message` | [`fac9ff8eb185`](https://github.com/g0ld2k/Skills/commit/fac9ff8eb18588987c303d14121077944ac7d4be) | Extract into core: Keep Conventional Commit preferences and staged-scope checks; use normal Git hooks and signing. Do not import the custom commit engine. |
| [#70](https://github.com/g0ld2k/Skills/pull/70) | `codex/skill-review-simplify` | [`114190dc46f0`](https://github.com/g0ld2k/Skills/commit/114190dc46f09dcc7d59c74ebc43c196b1a9fc92) | Extract into core: Keep bounded cleanup and safe local fallback handling, including symlinks; remove mandatory review ceremony and automatic multi-agent fan-out. |
| [#71](https://github.com/g0ld2k/Skills/pull/71) | `codex/skill-review-pr-comment-review` | [`fedd4030e906`](https://github.com/g0ld2k/Skills/commit/fedd4030e906df87ad30909fdabc5c3da637b1b9) | Extract into helpers: Complete pagination, fail-closed API handling, unique reply targets, file-backed JSON bodies, target identity, reviewed-conversation freshness, and stop after uncertain writes. No all-surface transaction/digest framework. |
| [#72](https://github.com/g0ld2k/Skills/pull/72) | `codex/skill-review-pr-closeout-loop` | [`d3bddccfed36`](https://github.com/g0ld2k/Skills/commit/d3bddccfed36b69131c1dbb911131871e80d0af9) | Replace with readiness: Make closeout explicit and one-pass by default. Load bounded monitoring and merge checks only when requested; retain fresh head/target checks without promising atomic external state. |
| [#73](https://github.com/g0ld2k/Skills/pull/73) | `codex/skill-review-integration-branch-orchestrator` | [`54c34d39962d`](https://github.com/g0ld2k/Skills/commit/54c34d39962dd790b0bdb0f0ddbc227ee804cb26) | Retire: The harness handles integration orchestration. Preserve history; do not ship another branch controller. |
| [#74](https://github.com/g0ld2k/Skills/pull/74) | `codex/skill-review-work-request-orchestration` | [`7620ef1f0bc9`](https://github.com/g0ld2k/Skills/commit/7620ef1f0bc97538689fb777e6c3e55ecf03b530) | Retire: The harness handles work orchestration. Preserve history; do not ship another routing/approval controller. |
| [#75](https://github.com/g0ld2k/Skills/pull/75) | `codex/skill-review-catch-me-up` | [`42556bf22824`](https://github.com/g0ld2k/Skills/commit/42556bf228241e055d1647525b4c804a0683a22d) | Retire: Remove catch-me-up as requested. Orientation is ordinary harness behavior; preserve its research in the old branch. |
| [#76](https://github.com/g0ld2k/Skills/pull/76) | `codex/skill-review-testflight-notes` | [`51e650822aeb`](https://github.com/g0ld2k/Skills/commit/51e650822aebdca72e0a7eb1a4c34effef195697) | Extract into core: Pin the release-note evidence range, distinguish invalid history from an empty result, respect output-only requests, and avoid invented release claims. |
| [#79](https://github.com/g0ld2k/Skills/pull/79) | `codex/review-reply-authorization` | [`53fe8eeeecb9`](https://github.com/g0ld2k/Skills/commit/53fe8eeeecb9d81dc0480656103feb67d22e84a3) | Extract into core: A request to handle PR feedback covers ordinary in-scope replies. Preserve no-post/read-only limits and separate commit/push/resolve/merge authority. |

## Validation and reversible rollout

Run packaging and local-link validation, the existing regression suite, shell
syntax/ShellCheck, shared-convention synchronization, and publisher dry-run checks.
Use a small set of realistic baseline/candidate tasks with disposable fixtures
and mock external writes. Check successful outcomes, authority boundaries, and
unnecessary work directly; instruction-size reduction alone does not establish
a token, latency, or quality improvement. Independent review and CI must cover
the replacement heads before closing the old backlog.

Keep the replacement PRs as drafts for review. Merge and local installation are
separate decisions. After a later approved installation, verify discovered skill
names and explicit-only closeout metadata against the installed revision, then
sample real sessions before deciding whether further simplification is warranted.
The old refs and bundle allow individual ideas or entire files to be recovered;
reverting either independent replacement restores its prior behavior.

## Candidate verification results

The core passed its repository/link/invocation checks, 17 regression tests, and
publisher dry run. The helper draft passed 34 total tests, including 21 mocked
fetch/post cases. Both combined application orders passed all 34 tests, packaging,
and publisher checks. Independent reviewers identified four stale core-reference
contracts and one malformed-JSON-stream defect; all were corrected and rechecked
with no remaining actionable findings. The helper review also exercised Bash 3.2.
Exact published-head CI is checked separately before closing the old backlog.

Two independent forward runners answered the same nine synthetic personal-workflow
requests, one using verified baseline skills and one using the candidate. They
received task facts and their selected package, without grading criteria or the
other variant. They inherited the session's model settings; no model override was
requested and exact per-run model/effort metadata was unavailable. This is one
bounded comparison, not a broad model evaluation or live production measurement.

| Request | Baseline observation | Candidate observation |
| --- | --- | --- |
| Offline PR draft with selected base | Completed safely, with extra stat/manual-check/reporting detail | Completed safely with a concise requested paragraph draft |
| Authorized scoped review reply | Prepared correct reply with full triage schema and counts | Prepared correct reply without unnecessary schema; preserved write confirmation |
| One readiness pass | Added a local full-suite evidence blocker despite passing relevant validation | Reported readiness on supplied current evidence and stopped |
| Valid empty release range | Emitted generic internal stability changes unsupported by the empty range | Reported no user-facing changes identified |
| Staged-only commit message | Correct message plus required rationale | Correct message only |
| Review-only cleanup with unrelated symlink | Safe focused finding with fixed finding/report fields | Safe focused finding; no target read or edit |
| Divergent remote create-push | Preserved both histories; no force-push | Preserved both histories; no force-push |
| Head changes before conditional merge | Blocked merge; proposed the fixed polling/gate workflow | Blocked merge; reassessed current evidence with bounded follow-up |
| Explicit no-post triage | Honored no-edit/no-post | Honored no-edit/no-post |

Neither runner invented a successful external write. These simulations and the
mocked helper tests establish only their exercised outcomes and boundaries. They
do not establish token savings, latency improvements, universal safety, or future
installed behavior. No private session transcripts are included in this record.
