# Monitoring and merge

Load only when the user requests waiting/monitoring or merge. Permission to
inspect or fix a PR does not imply these operations.

## Bounded monitoring

Use the user's wait budget. If none is supplied, make one follow-up after a
reasonable check interval and return the unchanged blocker; do not wait forever
or create a background automation. Follow the host's wait/tool limits. Resume
on new feedback within scope, or stop for conflicting feedback, missing authority,
unavailable required evidence, or a decision that polling cannot resolve.

Keep only the facts needed to resume safely: PR and head/base identity, allowed
actions, outstanding feedback/checks, validation scope, and the stop condition.
A compact task note is enough; no prescribed ledger schema is required.

## Before an authorized merge

- Confirm authority for this exact target branch and merge method. Promotion to
  a protected/default branch needs explicit coverage. Preserve a requested method;
  if unspecified, use the repository's configured policy or ask when ambiguous.
- Check the target branch's merge-queue rules before invoking `gh pr merge`: on a
  queue-required branch, it can enqueue the PR or enable auto-merge even without
  `--auto`. Queueing or auto-merge needs an explicitly requested workflow. If that
  scope is absent, or queue policy cannot be verified, report the blocker before
  invoking the merge operation; never bypass the queue.
- Re-fetch the PR head/base, reviews, full relevant feedback and required checks.
  A review of an old head or a body reaction alone is not proof of current-head
  approval. Honor repository approval rules and any additional user-selected
  review signal. Reassess approval after a material scope/body/base change.
- Required checks and relevant local validation must pass for the current code
  and integration context. Base movement can invalidate integration evidence;
  rerun affected checks or use a current verified merge result. Do not repeat
  unaffected successful checks solely to populate a ledger. If required validation
  cannot run, merge remains blocked unless the user/repository policy explicitly
  permits an alternative. Never waive branch protection.
- Clear actionable feedback and effective changes-requested reviews under the
  repository policy. Unclear/conflicting feedback remains a blocker. Resolve
  fixed threads only within the separately authorized resolution policy.
- Confirm mergeability and protect unrelated work. Use the platform's supported
  expected-head guard for merging. For `gh pr merge`, pass
  `--match-head-commit "$HEAD_SHA"` with `HEAD_SHA` set to the freshly fetched and
  validated PR head. Do not use admin bypass. If the guard is unavailable, report
  that capability gap rather than promising an atomic guarantee the tools do not
  provide.

Fresh reads and expected-head guards do not atomically bind every PR field.
Do not introduce custom full-body/thread transactions or queue/auto-merge as a
workaround. Honor the repository's supported controls and confirm the final
merged state and SHA; acceptance of a request is not proof that a merge completed.
