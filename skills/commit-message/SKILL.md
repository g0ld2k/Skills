---
name: commit-message
description: Use when generating a Conventional Commit message from staged changes, or when explicitly asked to commit after user approval.
license: MIT
---

# Commit Message

## Goal

Produce a high-quality Conventional Commit message from staged changes. When
committing, bind approval to a staged-tree identity and confirm it is unchanged
immediately before invoking normal `git commit`.

**Commit gate (single source for this skill):** two modes exist.
- `message-only` (default): never commit. A recorded approval scope alone does
  not switch modes; the caller must ask for the commit.
- `message+commit`: commit only with explicit user approval (for example:
  "commit it", "looks good, commit") or a caller-provided recorded approval
  scope that explicitly covers committing staged changes with the generated
  message.

## Workflow

### 0) Preflight and snapshot

Confirm the repository with `git rev-parse --is-inside-work-tree`. Stop and
report its error if the command fails or does not return `true`.

Run `git diff --cached --quiet` and preserve its exit status directly:

- `0`: no staged changes; stop and ask the user to stage the intended files.
- `1`: staged changes exist; continue.
- Any other status: report the command, status, and Git error, then stop.

For status `1`, run `git write-tree`. Stop on failure and keep its returned
`staged_tree` identity with the draft.

Then inspect the staged paths and summary:

```bash
git --no-pager diff --cached --name-only
git --no-pager diff --cached --stat
```

### 1) Collect evidence from staged diff

Use staged content as primary truth:

```bash
# Full staged patch for analysis
git --no-pager diff --cached

# Optional: staged file summary by status
git --no-pager diff --cached --name-status
```

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
check from Step 0 and run `git write-tree` again:

- If no staged changes remain, discard the draft and ask for the intended files
  to be staged.
- If the new tree differs from `staged_tree`, discard the draft, repeat staged
  evidence collection, and apply the same approval gate to the new tree and
  message. Attended approval requires fresh confirmation; recorded
  preauthorization must be re-evaluated for the new draft.
- If either Git command fails, report its command, status, and error, then stop.

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
