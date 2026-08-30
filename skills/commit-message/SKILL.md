---
name: commit-message
description: Use when generating a Conventional Commit message from staged changes, or when explicitly asked to commit after user approval.
license: MIT
---

# Commit Message

## Goal

Produce an evidence-based Conventional Commit message from staged changes and,
after the gate passes, commit the approved draft after a final staged-tree
check.

**Commit gate (single source for this skill):** two modes exist.
- `message-only` (default): never commit. A recorded approval scope alone does
  not switch modes; the caller must ask for the commit.
- `message+commit`: commit only with explicit user approval (for example,
  "commit it", "looks good, commit") or a caller-provided recorded approval
  scope that explicitly covers committing the current staged changes with the
  generated message.

## Definitions and guardrails

- `git diff --cached --quiet` status `0` means no staged changes, `1` means staged changes, and any status greater than `1` is a Git error that stops.
- `git write-tree` returns the immutable, non-empty staged-tree identity used to draft the message; keep it attached to the draft.
- Immediately before invoking `git commit`, re-read the status and run `git write-tree`
  again. An empty or different tree means staged content changed: discard the
  draft, re-read evidence, and repeat the applicable approval gate. Never
  commit a stale message.
- Attended approval is a fresh explicit confirmation. Recorded preauthorization
  is a caller-provided scope covering the current tree and message. After
  staged content changed, attended approval needs fresh confirmation and
  recorded preauthorization is re-evaluated; this is the same approval gate.
- Report the exact failing command, status, and Git error. Report SHA/subject
  only after `git commit` succeeds; a failed commit never produces success
  metadata.

## Workflow

### 0) Preflight checks

Run these first and preserve the status from each Git command:

```bash
if repo_check="$(git rev-parse --is-inside-work-tree)"; then
  :
else
  repo_status=$?
  printf 'Git error: `git rev-parse --is-inside-work-tree` exited %s.\n' \
    "$repo_status" >&2
  exit "$repo_status"
fi
if [ "$repo_check" != true ]; then
  printf 'Git error: this directory is not a Git work tree.\n' >&2
  exit 1
fi

if git diff --cached --quiet; then
  staged_status=0
else
  staged_status=$?
fi
case "$staged_status" in
  0)
    printf 'No staged changes; stage files before generating a message.\n'
    exit 0
    ;;
  1)
    ;;
  *)
    printf 'Git error: `git diff --cached --quiet` exited %s; preserve Git stderr above.\n' \
      "$staged_status" >&2
    exit "$staged_status"
    ;;
esac
```

Do not append `echo $?` to the staged-diff command: it would hide a Git error.
Do not draft or commit after a status greater than `1`.

### 1) Capture the draft tree and evidence

Capture the staged-tree identity before reading evidence. A successful,
non-empty `git write-tree` result is immutable for this draft:

```bash
if staged_tree="$(git write-tree)"; then
  :
else
  tree_status=$?
  printf 'Git error: `git write-tree` exited %s; drafting stopped.\n' \
    "$tree_status" >&2
  exit "$tree_status"
fi
if [ -z "$staged_tree" ]; then
  printf 'Git error: `git write-tree` returned an empty tree identity.\n' >&2
  exit 1
fi
```

Read all staged evidence through this checked reader; a failed name list, stat,
patch, or status result stops the draft. Re-run it after staged-content change:

```bash
run_staged_evidence() {
  if git --no-pager diff --cached "$@"; then
    :
  else
    evidence_status=$?
    printf 'Git error: `git --no-pager diff --cached %s` exited %s; preserve Git stderr above.\n' \
      "$*" "$evidence_status" >&2
    return "$evidence_status"
  fi
}

run_staged_evidence --name-only || exit $?
run_staged_evidence --stat || exit $?
run_staged_evidence || exit $?
run_staged_evidence --name-status || exit $?
```

### 2) Collect context

For terminology only, consult `CONTEXT.md`, `PRD.md`, `TASKS.md`, and `README.md`
if present; otherwise use the branch name and staged paths. Context never
overrides staged evidence.

### 3) Analyze and draft

Choose the commit type, optional scope, subject, and body from captured
evidence. Use Conventional Commit types (`feat`, `fix`, `refactor`, `perf`,
`docs`, `test`, `build`, `ci`, `chore`, `style`, or `revert`); use a top-level
scope when one area dominates, omit it for mixed areas, and keep the subject
imperative at 50–72 characters with a wrapped why-body. For breaking changes,
use `type(scope)!:` and add `BREAKING CHANGE: <impact>`. `style` means
formatting/whitespace, not functional visual style changes.

Do not claim test counts, issue IDs, or changes outside the staged diff.

### 4) Apply the approval gate

Show the staged-tree identity and proposed message:

```
Here's a suggested commit message:

<show formatted message>

Ready to commit when you confirm.
```

In `message-only` mode, return the proposal and stop. In `message+commit` mode,
require attended approval or verify recorded preauthorization. On every
re-draft, state that staged content changed and apply the same approval gate.

### 5) Re-check immediately before invoking `git commit`

After approval and immediately before invoking `git commit`, preserve the
staged-diff status again. Status `0` means staged content changed to an empty
index: throw away the draft and ask the caller to stage intended files. Status
`1` requires a fresh tree identity; every other status is a Git error that
stops:

```bash
if git diff --cached --quiet; then
  current_status=0
else
  current_status=$?
fi
case "$current_status" in
  0)
    printf 'Staged content changed: no staged changes remain; discard the draft and start again.\n' \
      >&2
    exit 0
    ;;
  1)
    if current_tree="$(git write-tree)"; then
      :
    else
      tree_status=$?
      printf 'Git error: `git write-tree` exited %s; commit stopped.\n' \
        "$tree_status" >&2
      exit "$tree_status"
    fi
    ;;
  *)
    printf 'Git error: `git diff --cached --quiet` exited %s; preserve Git stderr above.\n' \
      "$current_status" >&2
    exit "$current_status"
    ;;
esac

if [ "$current_status" -eq 1 ] && [ "$current_tree" != "$staged_tree" ]; then
  printf 'Staged content changed; discard the draft and repeat evidence and approval.\n' \
    >&2
  # Stop this draft. Return to Step 1 and preserve attended versus
  # recorded-preauthorization mode before another commit attempt.
  exit 1
fi
```

For a changed non-empty tree, discard the old message, return to Step 1, run
`run_staged_evidence` again, and apply Step 4. Bound re-drafts to at most 3
retries; then emit the repository Blocked Report and do not commit:

    BLOCKED: staged-tree-drift — staged content kept changing; no commit attempted.
    Last completed step: 5
    Would unblock: stabilize the intended staged index and start a new draft.

### 6) Write, commit, and report

Use one temporary message file and a portable cleanup trap; the `0` trap runs
after success, commit failure, or the signal trap's exit:

```bash
if commit_msg_file="$(mktemp "${TMPDIR:-/tmp}/commit-msg.XXXXXX")"; then
  :
else
  temp_status=$?
  printf 'Message-file setup failed: `mktemp` exited %s; no commit metadata is available.\n' \
    "$temp_status" >&2
  exit "$temp_status"
fi
cleanup() {
  rm -f "$commit_msg_file"
}
trap cleanup 0
trap 'exit 130' HUP INT TERM

if cat > "$commit_msg_file" <<'MSG'
<full commit message>
MSG
then
  :
else
  file_status=$?
  printf 'Message-file write failed: `cat > %s` exited %s; no commit metadata is available.\n' \
    "$commit_msg_file" "$file_status" >&2
  exit "$file_status"
fi

# Repeat Step 5 after writing the message file, immediately before this command.
if git commit -F "$commit_msg_file"; then
  :
else
  commit_status=$?
  printf 'Commit failed: `git commit -F %s` exited %s; preserve Git stderr above; no SHA or subject is reported.\n' \
    "$commit_msg_file" "$commit_status" >&2
  exit "$commit_status"
fi

if commit_result="$(git --no-pager log -1 --pretty=format:'%h %s')"; then
  printf '%s\n' "$commit_result"
else
  log_status=$?
  printf "Git error: final metadata lookup \`git --no-pager log -1 --pretty=format:'%h %s'\` exited %s; commit succeeded but SHA/subject unavailable.\n" \
    "$log_status" >&2
  exit "$log_status"
fi
```

The final log lookup is the first point where SHA and subject may be reported.
Normal repository hooks run as part of `git commit` after the final staged-tree
check and may modify the index. This skill binds the draft and approval to
`staged_tree`, but does not claim that the final commit tree must equal it.
Never auto-push.

## Output contract

### `message-only` (default)

Return the proposed message, a 1–3 line type/scope rationale, and:
`Ready to commit when you confirm.`

### `message+commit`

After successful `git commit`, return the checked
`git --no-pager log -1 --pretty=format:'%h %s'` result. For any failed gate or
command, report its exact command, status, and Git error; never report
SHA/subject as though the commit succeeded.

## References

- `references/conventions.md` for capability ladder, temp files, external text,
  and the Blocked Report format.
- `references/validation-scenarios.md` for executable coverage of the gates.
