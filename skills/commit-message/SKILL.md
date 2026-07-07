---
name: commit-message
description: Use when generating a Conventional Commit message from staged changes, or when explicitly asked to commit after user approval.
license: MIT
---

# Commit Message Skill (v2)

## Goal

Produce a high-quality commit message based on staged changes only.
Support two modes:
- `message-only` (default)
- `message+commit` (only after explicit user approval or a caller-provided
  recorded approval scope that covers committing)

Never commit automatically unless the caller provided a recorded approval scope
that explicitly covers committing staged changes with the generated message.

## Workflow

### 0) Preflight checks (required)

Run these first:

```bash
# Confirm repo and staged content
git rev-parse --is-inside-work-tree
git diff --cached --quiet; echo $?

# List staged files and stats
git --no-pager diff --cached --name-only
git --no-pager diff --cached --stat
```

Rules:
- If not in a git repo, stop and report the issue.
- If no staged changes, stop and ask user to stage files before generating a message.

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

Supported Conventional Commit types:
- `feat:` - New feature or functionality
- `fix:` - Bug fix
- `refactor:` - Code restructuring without behavior change
- `perf:` - Performance improvement
- `docs:` - Documentation only
- `test:` - Adding or updating tests
- `build:` - Build system or dependency build config
- `ci:` - CI configuration/workflow changes
- `chore:` - Tooling/maintenance not covered above
- `style:` - Formatting, whitespace (not visual style changes)
- `revert:` - Revert a prior commit

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

Ready to commit when you confirm.
```

If the caller requested `message+commit` mode AND provided a recorded approval
scope that explicitly covers committing staged changes, state that the commit
is preauthorized and continue to Phase 6 without another prompt. In the default
`message-only` mode, never commit — a recorded scope alone does not switch
modes; the caller must ask for the commit.

### 6) Commit only with explicit approval

Only if the user explicitly approves (for example: "commit it", "looks good,
commit", "please commit") or the caller provided a recorded approval scope that
explicitly covers committing staged changes with the generated message.

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
3. "Ready to commit when you confirm."

### B) `message+commit` (approval or recorded scope required)
After approval or recorded-scope verification:
1. Commit using `git commit -F`
2. Return commit SHA and subject from:
```bash
git --no-pager log -1 --pretty=format:'%h %s'
```

## Quality bar

Do:
- Prefer clarity over cleverness
- Keep subject specific and searchable
- Align wording with repository terminology
- Mention tests only when evidence exists

Do not:
- Use vague subjects like "update stuff"
- Invent issue references, test counts, or milestones
- Commit without explicit user confirmation or a recorded approval scope
- Describe unstaged/untracked changes as committed

## Portable examples

Feature:
```text
feat(auth): add refresh-token rotation for session renewal

Rotate refresh tokens on use and invalidate superseded tokens to
reduce replay risk during long-lived sessions.

Refs: security-session-hardening
```

Docs:
```text
docs(readme): clarify local setup and test commands

Document required environment variables and provide copy-paste setup
commands to reduce first-run friction.
```
