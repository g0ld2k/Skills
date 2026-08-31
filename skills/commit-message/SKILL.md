---
name: commit-message
description: Use when generating a Conventional Commit message from staged changes, or when explicitly asked to commit after user approval.
license: MIT
---

# Commit Message

## Goal

Produce a high-quality Conventional Commit message from staged changes. When
committing, bind approval and evidence to the draft identity: the commit parent
(`HEAD`) and staged tree. Confirm both are unchanged immediately before
invoking normal `git commit`.

**Commit gate (single source for this skill):** two modes exist.
- `message-only` (default): never commit. A recorded approval scope alone does
  not switch modes; the caller must ask for the commit.
- `message+commit`: commit only with explicit user approval (for example:
  "commit it", "looks good, commit") or a caller-provided recorded approval
  scope that explicitly covers committing staged changes with the generated
  message.

Approval is valid only for the displayed message and its exact
`(draft_parent, staged_tree)` identity pair.

## Workflow

### 0) Preflight and snapshot

Confirm the repository with `git rev-parse --is-inside-work-tree`. Stop and
report its error if the command fails or does not return `true`.

Before inspecting staged content, run `git rev-parse --quiet --verify MERGE_HEAD`
and preserve its tri-state status:

- `0`: a merge is in progress; stop clearly without drafting or committing.
  Do not model multi-parent merges in this skill.
- `1`: no `MERGE_HEAD`; continue.
- Any other status: report the command, status, and Git error, then stop.

```bash
if git rev-parse --quiet --verify MERGE_HEAD >/dev/null; then
  printf 'Merge in progress; resolve it before drafting a commit message.\n'
  exit 0
else
  merge_head_status=$?
fi
case "$merge_head_status" in
  1) ;;
  *)
    printf 'Git error: `git rev-parse --quiet --verify MERGE_HEAD` exited %s.\n' \
      "$merge_head_status" >&2
    exit "$merge_head_status"
    ;;
esac
```

Run `git diff --cached --quiet` and preserve its exit status directly:

- `0`: no staged changes; stop and ask the user to stage the intended files.
- `1`: staged changes exist; continue.
- Any other status: report the command, status, and Git error, then stop.

For status `1`, resolve and record `draft_parent` plus its immutable
`draft_base_tree`, then record `staged_tree` with `git write-tree`. A normal
`HEAD` is the parent. When `git rev-parse --verify HEAD` returns its unborn
status (normally status `128`), prove that `HEAD` is a symbolic ref whose ref
path is absent; record
`unborn:<ref>` as the parent and create `draft_base_tree` with
`git mktree </dev/null`. Use `git symbolic-ref --quiet HEAD`,
then confirm `git show-ref --verify --quiet <ref>` reports that ref as missing.
An existing or broken ref is a Git error, not an unborn repository. Preserve
every command's status and error.

The draft identity is `(draft_parent, staged_tree)`, with `draft_base_tree`
derived only from the recorded parent state. For a normal parent, use
`git rev-parse --verify "$draft_parent^{tree}"`; for an unborn parent it is
the immutable empty tree returned by `git mktree </dev/null>`. Never resolve a
separate live `HEAD^{tree}` baseline.

### 1) Collect evidence from the recorded identities

Use staged content as primary truth, but read it from the recorded parent's
baseline tree and staged tree rather than the live index. This prevents an
index change and reversal (an ABA race) from mixing evidence from different
snapshots:

```bash
run_git_evidence() {
  git --no-pager --attr-source="$staged_tree" diff --no-color --no-ext-diff --no-textconv "$draft_base_tree" "$staged_tree" "$@"
}

run_git_evidence --name-only || exit $?
run_git_evidence --stat || exit $?
run_git_evidence || exit $?
run_git_evidence --name-status || exit $?
```

All four evidence reads use only `draft_base_tree` and `staged_tree`; do not
read draft evidence with `git diff --cached` after the tree is recorded. Every
call explicitly exits on failure, reports its command and status, and stops.

### 2) Collect optional project context

If present, consult project docs for terminology only:
- `CONTEXT.md`
- `PRD.md`
- `TASKS.md`
- `README.md`

Fallback context when docs are missing:
- branch name
- staged file paths
- nearby commit history (`git log -n 10 --oneline`)

### 3) Analyze the changes

Identify commit type, optional scope, and subject:

Supported Conventional Commit types: `feat`, `fix`, `refactor`, `perf`,
`docs`, `test`, `build`, `ci`, `chore`, `style` (formatting/whitespace, not
visual style changes), `revert`.

Scope guidance (deterministic):
- Use top-level area if mostly one area changed (`api`, `ui`, `auth`, `docs`)
- If mixed areas, omit scope
- Do not invent product/team jargon absent from repo/user context

Breaking changes:
- Use `type(scope)!:` when clearly breaking
- Add footer: `BREAKING CHANGE: <impact>`

### 4) Generate commit message

Use this format:

```
<type>[optional scope]: <short description>

<optional body>

<optional footer>
```

Message rules:
- Subject in imperative mood, target 50-72 chars
- Body explains what/why, not implementation trivia
- Wrap body at ~72 chars
- Keep claims evidence-based from staged diff/context

Evidence rules (strict):
- Do not claim test counts unless directly supported by staged files/diff
- Do not reference issue IDs/phases unless provided by user/context/branch
- Do not mention unstaged or untracked changes

### 5) Present message for approval

Always show the proposed message first:

```
Here's a suggested commit message:

<show formatted message>

Draft parent: <draft_parent>
Staged tree: <staged_tree>

Ready to commit when you confirm.
```

If the commit gate (see Goal) passes on the preauthorized path, state that the
commit is preauthorized and continue to step 6 without another prompt.

### 6) Re-check and commit (gate in Goal must pass)

Create one unique message file with `mktemp`. Before writing the approved
message, register cleanup on normal exit and failure; handlers for `HUP`,
`INT`, and `TERM` must clean up and exit nonzero. A setup or write failure
stops the workflow and reports its command, status, and error.

Immediately before `git commit -F "$commit_msg_file"`, repeat the staged-status
check from Step 0 and run `git write-tree` again. Resolve `HEAD` with the same
normal/unborn procedure, recording `current_parent`; derive
`current_base_tree` only from that recorded parent with
`git rev-parse --verify "$current_parent^{tree}"` (or the empty tree if it is
still unborn):

```bash
if current_tree="$(git write-tree)"; then
  :
else
  tree_status=$?
  printf 'Git error: `git write-tree` exited %s.\n' "$tree_status" >&2
  exit "$tree_status"
fi
# Resolve HEAD again, preserving its status; use the unborn sentinel and empty
# tree when it is still unborn.
```

- If no staged changes remain, discard the draft and ask for the intended files
  to be staged.
- If the new tree differs from `staged_tree`, `current_parent` differs from
  `draft_parent`, or `current_base_tree` differs from `draft_base_tree`, discard
  the draft, repeat evidence collection from the new recorded identities, and
  apply the same approval gate to the new tree and parent. A changed commit
  parent requires this path even when the staged tree is unchanged, including
  a transition from an unborn parent to an actual parent. Attended approval
  requires fresh confirmation; recorded preauthorization must be re-evaluated
  for the new draft.
- If any Git command fails, report its command, status, and error, then stop.

The freshness condition is:

```bash
if [ "$current_tree" != "$staged_tree" ] ||
  [ "$current_parent" != "$draft_parent" ] ||
  [ "$current_base_tree" != "$draft_base_tree" ]; then
  printf 'Commit parent or staged tree changed; discard the draft before retrying.\n' >&2
  # Discard the old draft and restart at Step 1.
fi
```

Use normal `git commit -F` after the check. Repository hooks run normally and
may modify the index under repository policy; the drift gate covers changes
observed before the commit invocation. If the commit fails, report its command,
status, and Git error without reporting commit metadata. Cleanup runs on
success, failure, or interruption.

Only after a successful commit, read and report the SHA and subject with
`git --no-pager log -1 --pretty=format:'%h %s'`. Never auto-push unless
separately requested.

## Output contract

### A) `message-only` (default)
Return the Step 5 proposal plus a 1-3 line rationale for the type and scope.

### B) `message+commit` (commit gate passed)
After the final tree check and successful normal `git commit -F`, return the
checked SHA and subject. On failure, return the failing command, status, and Git
error without implying that a commit exists.

## References

- references/conventions.md for capability ladder, temp files, external-text, and Blocked Report conventions.
- When changing this skill, validate the behavior against
  [references/validation-scenarios.md](references/validation-scenarios.md).
