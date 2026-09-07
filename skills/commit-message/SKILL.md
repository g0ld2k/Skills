---
name: commit-message
description: Use when generating a Conventional Commit message from staged changes, or when explicitly asked to commit after user approval.
license: MIT
---

# Commit Message

## Goal

Produce a high-quality commit message based on staged changes only.

**Commit gate (single source for this skill):** two modes exist.
- `message-only` (default): never commit. A recorded approval scope alone does
  not switch modes; the user or caller must ask for the commit.
- `message+commit`: commit only with explicit user approval (for example:
  "commit it", "looks good, commit") or a caller-provided recorded approval
  scope that explicitly covers committing staged changes with the generated
  message.

## Workflow

### 1) Establish staged evidence

Establish that this is a Git repository and inspect the current staged diff.
An existing repository check can be reused; staged content must reflect the
message being generated. For example:

```bash
git --no-pager diff --cached
```

Use file summaries or statistics only when they help interpret the patch.
If this is not a repository, report the blocker. If the index is empty,
report that staged changes are needed; do not stage files as part of this skill.

### 2) Collect optional project context

Only when terminology is unresolved, consult relevant portions of project docs:
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

### 5) Present the message

Show the proposed message. In message-only mode, return it with the rationale.
When a commit was requested and the Goal gate passes, state the authorization
in use and continue without another confirmation. Ask only if the requested
commit lacks applicable authorization from the conversation or caller.

### 6) Commit (gate in Goal must pass)

Use safe file-based commit message flow (preferred across CLIs):
```bash
commit_msg_file="$(mktemp "${TMPDIR:-/tmp}/commit-msg.XXXXXX")"
cat > "$commit_msg_file" <<'MSG'
<full commit message>
MSG
git commit -F "$commit_msg_file"
rm -f "$commit_msg_file"
```

Alternative (subject only):
```bash
git commit -m "<subject>"
```

Do not auto-push after commit unless separately requested.

## Output contract

### A) `message-only` (default)
Return:
1. Proposed commit message
2. 1-3 line rationale (type/scope choice)

### B) `message+commit` (commit gate passed)
1. Commit using `git commit -F`
2. Return commit SHA and subject from:
```bash
git --no-pager log -1 --pretty=format:'%h %s'
```

## References

- references/conventions.md for capability ladder, temp files, external-text, and Blocked Report conventions.

## Validation

When changing scope or authorization behavior, use the relevant
[validation scenarios](references/validation-scenarios.md).
