---
name: testflight-notes
description: Generate user-facing TestFlight build notes from git history. Use when asked for TestFlight notes, build notes, release notes, or a summary of changes since a timeframe, tag, or commit.
tools:
  - bash
  - git
  - read
---

# TestFlight Notes Generator

Generate concise, tester-friendly TestFlight build notes from git history.

This skill is designed to work in Codex CLI, Codex Desktop, and Copilot CLI.

## Inputs

Prefer one of these user inputs:
- A timeframe (for example: `last 10 days`, `since 2 weeks ago`)
- A starting commit or tag (for example: `abc1234`, `build-151`)

If the user does not provide one, use this fallback order:
1. Since latest tag to `HEAD`
2. Last 14 days if no tags exist

State the assumption before output.

## Workflow

### 1) Determine commit range

Use one of:

```bash
# By timeframe
git --no-pager log --oneline --since="<natural language date>"

# From commit or tag
git --no-pager log --oneline <START>..HEAD

# Since latest tag fallback
git --no-pager log --oneline "$(git describe --tags --abbrev=0)"..HEAD
```

### 2) Extract rich commit context

Collect structured commit data for the selected range:

```bash
git --no-pager log \
  --pretty=format:"%H%x09%h%x09%s%x09%b%x09%an%x09%ad" \
  --date=short \
  <RANGE>
```

Then inspect full bodies for candidate commits:

```bash
git --no-pager show <SHA> --format="%B" --no-patch
```

Always inspect merge/squash commit bodies in range; they often contain user-facing summaries.

### 3) Classify user-facing changes

Do not rely only on `feat:` and `fix:` prefixes.

Apply `references/classification-rules.md`:
- Include user-visible behavior changes even if commit type is `refactor`, `chore`, or unprefixed
- Exclude internal-only changes (CI, tests, tooling, formatting, automation)
- Prioritize effect on testers over implementation detail

### 4) Deduplicate and synthesize

Many ranges contain multiple commits for one feature/fix. Collapse these into one final entry per logical change:
- Merge follow-up commits into the original user-facing change
- Keep the clearest wording from the richest commit body
- Avoid repeating the same behavior change across NEW/IMPROVED/FIX

Use `references/format-guide.md` for final structure and style.

### 5) Assign labels and platform scope

For each final entry:
- Label exactly one of `NEW`, `IMPROVED`, or `FIX`
- Add platform suffix only when confidently platform-specific:
  - `NEW (iOS): ...`
  - `FIX (macOS): ...`
- If uncertain, omit platform suffix and keep it cross-platform

Use platform heuristics from `references/classification-rules.md`.

### 6) Enforce length budget

Hard limit is 4000 characters.

Before final output:
1. Target <= 3800 chars (safety margin)
2. If over budget, shorten in this order:
   - Remove secondary sentence details
   - Merge similar improvements
   - Drop lowest-impact IMPROVED items
3. Keep all high-impact FIX items whenever possible

### 7) Quality gate

Before printing, verify:
- Plain text only (no markdown bullets, no `#` headings)
- Starts with `What's new in this build:`
- Group order is NEW -> IMPROVED -> FIX
- No duplicate behavior entries
- Language is tester-facing, not implementation-heavy
- No trailing blank line

### 8) Output

Print only the final notes block to terminal. Do not save to a file unless explicitly requested.

## Operational Notes

- If range resolves to no user-facing changes, output:

```text
What's new in this build:

IMPROVED: Internal quality and stability updates for this build.
```

- If commit history is noisy, prefer fewer high-confidence notes over many speculative notes.
- When asked, include a short "excluded changes" summary after the notes, but only as a separate optional section.
