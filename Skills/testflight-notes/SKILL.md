---
name: testflight-notes
description: Generate user-facing TestFlight build notes from git history for the Zoner project. Use when asked to generate TestFlight notes, build notes, release notes, or summarize what changed since a previous build or commit. Accepts a timeframe (e.g. "last 10 days") or a starting commit SHA or tag.
---

# TestFlight Notes Generator

Generate concise, tester-friendly TestFlight build notes from git history.

## Workflow

### 1. Determine the commit range

Ask the user for one of:
- A **timeframe** — e.g. "10 days", "since 2 weeks ago", "last 7 days"
- A **starting commit SHA or tag** — e.g. `build-151` or `abc1234`

If the user already provided this in their message, skip asking.

### 2. Extract relevant commits

Run the appropriate git command:

```bash
# By timeframe
git --no-pager log --oneline --since="<N> days ago"

# From a commit SHA or tag
git --no-pager log --oneline <SHA>..HEAD
```

Then fetch full details for any `feat` or `fix` prefixed commit (skip `test`, `refactor`, `docs`, `ci`, `chore`, `build`):

```bash
git --no-pager show <SHA> --format="%B" --no-patch
```

Read merge commit bodies too — they often contain the richest user-facing descriptions.

### 3. Synthesize user-facing changes

For each relevant commit, extract what the user actually experiences. Ignore internal refactors, test harness changes, CI fixes, and screenshot automation even when wrapped in a `fix` commit.

Read `references/format-guide.md` to correctly format and label the output.

### 4. Output

Print the final notes to the terminal. Do not save to a file.
