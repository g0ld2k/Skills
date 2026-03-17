---
name: pr-generator
description: Generate and optionally publish high-quality GitHub pull requests using a deterministic, evidence-based workflow. Produces concise PR titles and markdown bodies with goal, change summary, testing, risks, and rollout notes. Always requires explicit user approval before creating or updating a PR.
tools:
  - bash
  - view
  - edit
  - grep
  - glob
---

# PR Generator (v2)

## When to Use

Use this skill when a user asks to:
- generate a PR description
- create a pull request
- improve/update an existing PR body/title

## Runtime Compatibility

This skill is designed for:
- Codex CLI
- Codex Desktop
- GitHub Copilot CLI

Capability strategy:
1. Prefer `gh` + `git` CLI.
2. If `gh` is unavailable but GitHub MCP is available, use MCP equivalents.
3. If neither path can create/update PRs, stop and report the missing capability.

## Non-Negotiable Guardrails

- Never create or update a PR without explicit user approval.
- Never invent test execution, issue links, or validation results.
- Never claim "tests passed" unless commands were actually run and succeeded.
- Never use destructive git commands unless explicitly requested.
- Never silently choose a base branch; detect and report it.

## Workflow

### Phase 0: Preflight

Run these first:

```bash
git rev-parse --is-inside-work-tree
git --no-pager branch --show-current
git fetch --prune origin
if command -v gh >/dev/null 2>&1; then
  gh --version
  gh auth status
else
  echo "gh not found; use GitHub MCP fallback for PR create/update."
fi
```

Stop if:
- not in a git repo
- current branch is `main` or `master`
- `gh` auth is invalid and no MCP fallback is available

If `gh` is unavailable but GitHub MCP is available:
- resolve repo + current branch context
- detect existing open PR for the branch
- create PR when none exists, or update PR title/body when one exists
- follow the same approval and truthfulness guardrails as the `gh` path

### Phase 1: Detect Base Branch Deterministically

Detect base branch once and reuse it for all later steps.

```bash
BASE_BRANCH="$(bash scripts/detect_base_branch.sh)"
echo "Using base branch: ${BASE_BRANCH:-<none>}"
```

Stop if `BASE_BRANCH` is empty.

### Phase 2: Collect Branch Evidence

```bash
# Commits ahead of base
git --no-pager log "origin/$BASE_BRANCH"..HEAD --oneline

# File stats and patch context
git --no-pager diff "origin/$BASE_BRANCH"...HEAD --stat
git --no-pager diff "origin/$BASE_BRANCH"...HEAD --name-status
git --no-pager diff "origin/$BASE_BRANCH"...HEAD
```

Stop if:
- no commits ahead
- no changed files

### Phase 3: Optional Project Context

If present, read:
- `CONTEXT.md`
- `PRD.md`
- `TASKS.md`
- `README.md`

Use only to improve terminology and milestone framing; do not override diff evidence.

### Phase 4: Testing Evidence Collection

Capture two separate signals:

1) **Tests Changed** (from diff paths)

```bash
git --no-pager diff "origin/$BASE_BRANCH"...HEAD --name-only | grep -Ei '(^|/)(test|tests|__tests__|specs?)(/|$)|(_test\.|\.test\.|\.spec\.)'
```

2) **Tests Run** (executed in this session)
- Record only commands actually run (for example `swift test`, `make test`, `npm test`).
- If no tests are run, explicitly state: `Not run in this session`.

### Phase 5: Generate Draft PR Title and Body

Title rules:
- Conventional Commit style: `<type>(optional-scope): <subject>`
- Allowed types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, `chore`
- Keep subject specific and concise.

Body template:

```markdown
### Goal
[1-2 sentences: what this PR does and why]

### What Changed
- **[Category]:** [Key change and impact]
- **[Category]:** [Key change and impact]

### Testing
- **Tests Changed:** [Summary]
- **Tests Run:** [Exact commands + results, or "Not run in this session"]

### Files Changed
[X files, +Y/-Z lines]

### Risks / Breaking Changes
- [Known risks, migrations, compatibility notes, or "None identified"]

### How to Validate
1. [Manual scenario with expected result]
2. [Manual scenario with expected result]
3. **Automated:** `[test command(s)]`

### Notes
[Issue links, phase completion, follow-up tasks]
```

Category guidance: `API`, `Models`, `UI`, `Business Logic`, `Data`, `Infra/Config`, `Docs`, `Testing`, `Performance`, `Security`.

### Phase 6: Present Draft for Approval

Always show:
- proposed PR title
- full PR body
- detected base branch
- whether this will create a new PR or update an existing PR

Ask for explicit approval before publish/update.

### Phase 7: Create or Update PR (Post-Approval Only)

1) Check whether an open PR already exists for this branch:

```bash
BRANCH="$(git branch --show-current)"
gh pr view "$BRANCH" --json number,url,title,baseRefName 2>/dev/null
```

2) Write body to a temp file (portable, quote-safe, and usable across steps):

```bash
pr_body_file="$(mktemp "${TMPDIR:-/tmp}/pr-body.XXXXXX.md")"
cat > "$pr_body_file" <<'MD'
<generated markdown body>
MD
# Optional cleanup after publish: rm -f "$pr_body_file"
```

3) Publish action:

- If PR exists: update it
```bash
gh pr edit <number> --title "<title>" --body-file "$pr_body_file"
```

- If PR does not exist: create it
```bash
git push -u origin "$BRANCH"
gh pr create \
  --title "<title>" \
  --body-file "$pr_body_file" \
  --base "$BASE_BRANCH" \
  --head "$BRANCH"
```

4) On success:
- show PR URL
- summarize title/base/head

5) On failure:
- report exact failing command and stderr
- suggest the next concrete fix (auth, permissions, branch push, base mismatch)

## Output Contract

When done, provide:
1. PR title
2. PR body
3. Base/head branches
4. Create vs update decision
5. Tests changed
6. Tests run (or explicitly not run)
7. PR URL (after publish)

## References

- [style-guide.md](references/style-guide.md)
- [title-heuristics.md](references/title-heuristics.md)
- [testing-language.md](references/testing-language.md)
- [failure-handling.md](references/failure-handling.md)
