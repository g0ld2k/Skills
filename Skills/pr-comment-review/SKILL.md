---
name: pr-comment-review
description: Review and address GitHub PR feedback with a deterministic workflow: fetch unresolved review threads, triage each comment, apply approved fixes, validate changes, and post precise replies. Use when asked to review PR comments, respond to review feedback, or close out PR review items in Codex or Copilot CLI.
tools:
  - bash
  - view
  - edit
  - grep
  - glob
---

# PR Comment Review

## When to Use

Use this skill when a user asks to:
- review PR comments
- respond to reviewer feedback
- address review threads on a pull request

## Runtime Compatibility

This skill is designed for:
- Codex CLI
- Codex Desktop
- GitHub Copilot CLI

Use a capability-first strategy:
1. Prefer GitHub MCP tools if available.
2. Otherwise use `gh api` / `gh pr` commands.
3. If neither is available, stop and report the missing capability.

### MCP Fallback (No `gh`)

If `gh` is unavailable but GitHub MCP is available:
- Fetch PR metadata (owner/repo/number, branch context).
- Fetch review threads/comments including resolved state.
- Triage only comments from unresolved threads.
- Post replies via MCP comment-reply capability.

Maintain the same guardrails and output contract as the `gh` path.

## Non-Negotiable Guardrails

- Never post replies before user approval.
- Never claim a fix unless it is implemented or intentionally declined.
- Never reply to resolved review threads.
- Never continue to posting if validation fails.
- Never force-push or use destructive git commands unless explicitly requested.

## Workflow

### Phase 0: Preflight

Collect PR target from any of:
- PR URL
- `{owner}/{repo}` + PR number
- current branch PR via `gh pr view`

Validate environment:
```bash
git rev-parse --is-inside-work-tree
gh --version
gh auth status
```

If `gh` is unavailable, use equivalent MCP tools when possible.

### Phase 1: Fetch Unresolved Review Feedback

Fetch review comments from unresolved threads only.

Preferred helper:
```bash
bash scripts/fetch_unresolved_review_comments.sh <owner> <repo> <pr_number>
```

This script filters out threads where `isResolved == true`, so we do not triage or address them.

Also fetch issue comments only for context (not as required actions):
```bash
gh api repos/<owner>/<repo>/issues/<pr_number>/comments --paginate
```

### Phase 2: Triage and Recommendation

For each unresolved review comment, produce:
- `comment_id`
- `file:line`
- `validity` (`valid`, `partial`, `invalid`)
- `priority` (`high`, `medium`, `low`)
- `decision` (`fix`, `reply`, `discuss`)
- `planned_action`
- `draft_reply`

Use rubric: [decision-rubric.md](references/decision-rubric.md)
Use reply patterns: [reply-templates.md](references/reply-templates.md)

Present grouped plan to user:
- `fix` items
- `reply-only` items
- `discuss` items

Get explicit approval before coding.

### Phase 3: Implement Approved Fixes

Apply minimal, targeted edits only for approved `fix` items.

Validation policy:
- Run targeted tests first.
- Run broader suite if requested or if risk is high.
- If tests fail, stop and report before any posting.

Commit/push only with user approval.

### Phase 4: Post Replies

Before posting each reply:
- Re-check the thread is still unresolved.
- Skip and report if it became resolved during the session.

Preferred helper (supports dry run):
```bash
bash scripts/post_pr_replies.sh --owner <owner> --repo <repo> --pr <pr_number> --replies-file <path> --dry-run
bash scripts/post_pr_replies.sh --owner <owner> --repo <repo> --pr <pr_number> --replies-file <path>
```

Require explicit user approval before the non-dry-run step.

## Output Contract

Final summary must include:
- unresolved comments fetched
- comments triaged
- comments fixed vs reply-only vs discuss
- tests run and result
- replies posted
- replies skipped because thread already resolved
- commit SHA / branch (if code changed)

## Quick Commands

```bash
# Fetch unresolved review comments
bash scripts/fetch_unresolved_review_comments.sh <owner> <repo> <pr_number>

# Build triage markdown template
bash scripts/build_triage_template.sh --input unresolved-comments.json

# Post replies from JSON (safe preview first)
bash scripts/post_pr_replies.sh --owner <owner> --repo <repo> --pr <pr_number> --replies-file replies.json --dry-run
```

## References

- [github-api.md](references/github-api.md)
- [decision-rubric.md](references/decision-rubric.md)
- [reply-templates.md](references/reply-templates.md)
