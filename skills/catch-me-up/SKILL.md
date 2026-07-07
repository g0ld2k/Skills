---
name: catch-me-up
description: Use when the user asks to get oriented in unfamiliar code, explain architecture, identify conventions or idioms, trace how a feature works, explain unfamiliar syntax or APIs, assess test coverage, or understand code history.
license: MIT
---

# Catch Me Up

Build the user's mental model of unfamiliar code, architecture, or technology. Prioritize comprehension over generation: explain before suggesting changes.

This is a read-only comprehension skill. During this skill, do not edit files, produce review findings, fix bugs, stage changes, create commits, or publish pull requests unless the user separately asks for that work after the catch-up brief.

## Guardrails

- Ground claims in evidence: file paths, symbols, docs, tests, diffs, git history, PR metadata, or user-provided context.
- Do not invent history, rationale, ownership, test coverage, or architectural intent.
- If evidence is missing, say what was checked and what remains unknown.
- Keep the first pass scoped to the user's question. Do not map the whole repository unless asked.
- Use `History` only from available evidence such as `git log`, `git blame`, PRs, issues, changelogs, comments, or user-provided context.
- If the target is a pull request, use this skill only for lightweight comprehension of the diff and touched code. A full PR comprehension or review workflow belongs in a separate PR-focused skill.

## Workflow

### Step 1: Determine Exploration Mode

Identify the target from the user's request:
- repository or workspace
- branch, commit, diff, file, symbol, feature, behavior, architecture, or technology
- desired depth: quick orientation, detailed trace, or mode-specific answer

Ask one concise question only if the target is ambiguous and cannot be inferred from local context.

Select modes using these trigger signals:

| Mode | Trigger signals |
| --- | --- |
| Architecture | "how is this structured", "where does this fit", "what owns this", "system design", "architecture" |
| Convention | "what patterns", "what is the standard", "how do they usually", "idioms", "style" |
| Feature Trace | "how does X work", "trace", "walk me through", "flow", "from click to result", "from request to response" |
| Syntax/API | "what does this syntax mean", "what is this API", "why this construct", "explain this type", "framework magic" |
| Testing | "how is this tested", "what covers this", "test strategy", "missing tests", "how would I validate" |
| History | "why was this changed", "who changed this", "when did this appear", "rationale", "regression history" |

For broad "catch me up" requests, choose the modes that appear useful after the first evidence pass. Do not force every mode if it would create noise.

### Step 2: Execute Exploration

Start with the smallest useful evidence set.

For local repositories, prefer:

```bash
pwd
git status --short --branch
rg --files
```

Then inspect only relevant files, docs, tests, and configuration. If history matters and the directory is a git repo, use focused commands such as:

```bash
git --no-pager log --oneline -- <path>
git --no-pager blame -L <start>,<end> -- <path>
```

Read the sections of `references/exploration-modes.md` matching the modes selected in Step 1, plus its Depth Guardrails table. Treat those sections as the canonical source for mode details, evidence examples, and depth limits.

For narrower requests, emphasize the relevant modes and briefly note which modes were skipped or minimized.

### Step 3: Produce The Catch-Up Brief

Use this structure unless the user asks for a different format:

1. **Short Orientation:** 2-4 sentences explaining the area and why it matters.
2. **Evidence Checked:** concise list of files, docs, diffs, tests, or history inspected.
3. **Exploration Modes:** a table by default, with one row per relevant mode.
4. **Confidence And Gaps:** what is solid, what is inferred, and what remains unknown.
5. **Next Probes:** 2-5 concrete follow-up checks or questions.

Default table:

| Mode | What matters | Evidence |
| --- | --- | --- |
| Architecture | ... | `path/file.ext:12` |

Add a Mermaid diagram or ASCII diagram when it makes a code flow, dependency relationship, lifecycle, or request path easier to understand. Keep diagrams small enough to verify from inspected evidence.

## Output Contract

Final answers should:
- prioritize orientation over exhaustive detail
- include clickable or exact local file references when possible
- distinguish confirmed facts from inferences
- mention history only when sourced
- use a table by default for exploration modes
- include Mermaid or ASCII diagrams only when they clarify the mental model
- end with concrete next probes, not generic offers

## References

- `references/exploration-modes.md` for mode definitions and evidence examples.
