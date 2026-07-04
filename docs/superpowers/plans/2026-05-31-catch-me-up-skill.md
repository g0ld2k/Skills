# Catch Me Up Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable `catch-me-up` skill that helps an agent build a mental model of unfamiliar code, architecture, technology, features, or code paths through evidence-backed exploration modes.

**Architecture:** The skill is a compact comprehension workflow, not a code review workflow. `SKILL.md` defines mode-selection triggers, depth guardrails, evidence gathering, and the required table-first output contract; a single reference file defines the exploration modes and examples so the main skill stays lean.

**Tech Stack:** Markdown-based Codex skill in this personal `Skills/` repo, using the existing `scripts/new-skill.sh` scaffold and shell-based validation.

---

## What Is Missing From The Gemini Draft

- Evidence discipline: the draft names the six categories but does not require file paths, line numbers, diffs, docs, tests, or git history as support.
- Scope control: it does not distinguish comprehension from review, implementation, or bug fixing.
- Trigger clarity: it needs precise frontmatter so Codex loads it for "catch me up", "orient me", "explain this PR", "trace this feature", and similar requests.
- Mode selection: the source screenshots show a dedicated "Step 1: Determine exploration mode" table with trigger signals, so the skill should choose modes intentionally rather than always running every mode.
- Depth control: the source screenshots show "Step 2: Execute exploration" and "Depth guardrails", so the skill should define sampling limits for each mode.
- Progressive disclosure: the mode definitions should live in `references/exploration-modes.md`, keeping `SKILL.md` short.
- Output contract: the skill needs a repeatable table-first structure that surfaces confidence, unknowns, and next probes, with Mermaid or ASCII diagrams when they clarify a flow.
- History guardrails: history should come from `git log`, `git blame`, PR metadata, or user-provided context; it must not be guessed.
- External video dependency: the skill should be inspired by the described idea, not depend on reconstructing proprietary or unavailable presenter text.

## Resolved Decisions From User Feedback

1. Skill name: use `catch-me-up`.
2. Scope: keep `catch-me-up` focused on codebase and feature comprehension. A richer PR comprehension workflow should be a separate future skill because it needs issue-tracker context, diff summarization, optional review concerns, and diagrams.
3. Mode triggering: Architecture, Convention, Feature Trace, Syntax/API, Testing, and History should run only when appropriate to the user's question and gathered evidence.
4. Output shape: use a table by default. Add Mermaid or ASCII diagrams when they make a code flow, dependency relationship, or lifecycle easier to understand.

## Future Skill Candidate: PR Catch-Up

Do not implement this in the first `catch-me-up` skill. Capture it as a follow-on idea:

- Name candidate: `pr-catch-up` or `pr-comprehension`.
- Inputs: GitHub PR, issue tracker item, branch diff, local patch, or provided diff.
- Evidence: issue description, PR description, comments when available, changed files, tests changed, dependency and call-flow impact.
- Output: overview of changes, table of affected areas, Mermaid or ASCII flow diagram when useful, strengths, optional areas of concern, missing tests, possible architecture drift, race conditions, likely bugs, and open questions.
- Guardrail: review findings are optional and should be clearly labeled as comprehension-oriented concerns, not a full approval/blocking review unless the user asks.

## File Structure

- Create: `Skills/catch-me-up/SKILL.md`
  - Skill frontmatter, trigger description, guardrails, workflow, and output contract.
- Create: `Skills/catch-me-up/references/exploration-modes.md`
  - Trigger signals, depth guardrails, evidence sources, and examples for Architecture, Convention, Feature Trace, Syntax/API, Testing, and History.
- Create: `Skills/catch-me-up/scripts/.gitkeep`
  - Keeps the scaffolded scripts directory present without adding unnecessary scripts.
- No change: `scripts/new-skill.sh`
  - Existing scaffolding is sufficient.
- No change: `README.md`
  - The repo already documents the skill layout and add-new-skill flow.

### Task 1: Scaffold The Skill

**Files:**
- Create: `Skills/catch-me-up/SKILL.md`
- Create: `Skills/catch-me-up/references/`
- Create: `Skills/catch-me-up/scripts/`

- [ ] **Step 1: Verify repo state before editing**

Run:

```bash
git rev-parse --is-inside-work-tree
git status --short --branch
```

Expected: first command prints `true`. The second command may show detached `HEAD`; if it does, create or switch to the intended feature branch before editing.

- [ ] **Step 2: Scaffold the skill folder**

Run:

```bash
bash scripts/new-skill.sh catch-me-up "Build a mental model of unfamiliar code, architecture, technology, features, or code paths using evidence-backed exploration modes."
```

Expected:

```text
Created: Skills/catch-me-up
```

- [ ] **Step 3: Confirm scaffolded files**

Run:

```bash
find Skills/catch-me-up -maxdepth 2 -type d -o -type f | sort
```

Expected:

```text
Skills/catch-me-up
Skills/catch-me-up/SKILL.md
Skills/catch-me-up/references
Skills/catch-me-up/scripts
```

- [ ] **Step 4: Commit scaffold**

Run:

```bash
git add Skills/catch-me-up
git commit -m "chore: scaffold catch-me-up skill"
```

Expected: commit succeeds with the scaffolded skill files only.

### Task 2: Write The Exploration Mode Reference

**Files:**
- Create: `Skills/catch-me-up/references/exploration-modes.md`

- [ ] **Step 1: Create `exploration-modes.md`**

Replace `Skills/catch-me-up/references/exploration-modes.md` with:

```markdown
# Exploration Modes

Use these modes as lenses, not as rigid boxes. Prefer concrete evidence over broad summaries. When evidence is missing, say what was checked and what remains unknown.

## Mode Trigger Signals

| Mode | Trigger signals |
| --- | --- |
| Architecture | "how is this structured", "where does this fit", "what owns this", "system design", "architecture" |
| Convention | "what patterns", "what is the standard", "how do they usually", "idioms", "style" |
| Feature Trace | "how does X work", "trace", "walk me through", "flow", "from click to result", "from request to response" |
| Syntax/API | "what does this syntax mean", "what is this API", "why this construct", "explain this type", "framework magic" |
| Testing | "how is this tested", "what covers this", "test strategy", "missing tests", "how would I validate" |
| History | "why was this changed", "who changed this", "when did this appear", "rationale", "regression history" |

For broad "catch me up" requests, choose the modes that appear useful after the first evidence pass. Do not force every mode if it would create noise.

## Depth Guardrails

| Mode | Sampling limit |
| --- | --- |
| Architecture | Read top-level docs/config plus the smallest set of entry points and boundary files that explain ownership. |
| Convention | Compare 2-4 nearby or analogous files before naming a convention. |
| Feature Trace | Follow one primary happy path end to end, then mention important branches only if they affect comprehension. |
| Syntax/API | Explain only constructs visible in the target area; do not teach the full language or framework. |
| Testing | Inspect nearby tests and obvious test commands/config; do not run expensive test suites unless the user asks. |
| History | Use focused `git log`/`git blame` or provided PR/issue history for relevant paths only; do not infer rationale from silence. |

## Architecture

Explain the system shape and where the requested code fits.

Look for:
- entry points, boundaries, and ownership
- data flow and control flow between modules
- external services, persistence, queues, UI surfaces, or platform APIs
- abstractions that protect the rest of the system from local details

Evidence examples:
- `README.md`, `CONTEXT.md`, `TASKS.md`, architecture docs
- package manifests, app entry points, route definitions, dependency wiring
- filenames and symbols that define boundaries

Output should answer:
- What are the main moving parts?
- Which part owns the behavior being discussed?
- What dependencies matter for understanding this area?

## Convention

Identify local patterns the codebase expects contributors to follow.

Look for:
- naming and file organization patterns
- error handling, dependency injection, state management, or concurrency idioms
- project-specific helpers, wrappers, or test fixtures
- style decisions repeated near the target code

Evidence examples:
- adjacent files that solve similar problems
- lint or formatting config
- test utilities and shared fixtures
- contributor docs or agent instructions

Output should answer:
- What local idioms should a change preserve?
- Which existing helpers should be reused?
- What would look out of place in this codebase?

## Feature Trace

Trace how a user request, event, data record, or API call moves through the system.

Look for:
- source entry point
- validation and transformation steps
- state changes, persistence, side effects, and emitted outputs
- user-visible or caller-visible result

Evidence examples:
- route, command, view, intent, controller, reducer, model, store, or service files
- tests that exercise the path end to end
- logs, fixtures, or sample data

Output should answer:
- Where does the flow start?
- What sequence of files and functions does it pass through?
- Where does the observable result happen?

## Syntax/API

Explain non-obvious implementation details without teaching the whole language.

Look for:
- dense expressions, generics, macros, decorators, property wrappers, protocols, traits, or type-level constraints
- async, concurrency, lifecycle, memory, or ownership details
- unusual build configuration or generated code interactions

Evidence examples:
- the exact symbols or lines that are hard to read
- compiler or framework docs only when local code is not enough

Output should answer:
- What does this construct do here?
- Why might this syntax have been chosen?
- What mistake would a new contributor be likely to make?

## Testing

Explain how confidence is established for this area.

Look for:
- unit, integration, UI, snapshot, fixture, or contract tests
- test helper patterns and naming conventions
- gaps where behavior is important but not covered
- commands that appear to run the relevant tests

Evidence examples:
- nearby test files
- package scripts, Makefiles, CI config, Xcode schemes, or test manifests
- test names that map to the feature trace

Output should answer:
- What tests already cover this behavior?
- What test command is likely relevant?
- What coverage gaps remain?

## History

Explain why code exists or how it evolved only when evidence is available.

Look for:
- `git log`, `git blame`, commit messages, PR descriptions, linked issues, or changelog entries
- comments that explain rationale
- migrations or compatibility code

Evidence examples:
- commit hashes and subjects
- PR or issue references provided by the user
- blame output for relevant lines

Output should answer:
- What historical reason is visible?
- Which changes introduced or reshaped this area?
- What cannot be determined from available history?
```

- [ ] **Step 2: Validate reference has all six modes**

Run:

```bash
for mode in Architecture Convention "Feature Trace" "Syntax/API" Testing History; do
  rg "^## ${mode}$" Skills/catch-me-up/references/exploration-modes.md
done
```

Expected: one matching heading for each mode.

- [ ] **Step 3: Commit reference**

Run:

```bash
git add Skills/catch-me-up/references/exploration-modes.md
git commit -m "docs: define catch-me-up exploration modes"
```

Expected: commit succeeds with only the reference file change.

### Task 3: Replace The Skill Body

**Files:**
- Modify: `Skills/catch-me-up/SKILL.md`

- [ ] **Step 1: Replace `SKILL.md`**

Replace `Skills/catch-me-up/SKILL.md` with:

```markdown
---
name: catch-me-up
description: "Build a mental model of unfamiliar code, architecture, technology, features, or code paths using evidence-backed Architecture, Convention, Feature Trace, Syntax/API, Testing, and History exploration modes."
tools:
  - bash
  - view
  - grep
  - glob
---

# Catch Me Up

Build the user's mental model of unfamiliar code, architecture, or technology. Prioritize comprehension over generation: explain before suggesting changes.

Use this skill when the user asks to get oriented, catch up, understand a codebase area, trace a feature, explain unfamiliar syntax or APIs, understand test coverage, or map how unfamiliar code works.

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

Read `references/exploration-modes.md` when using this skill.

Apply these depth guardrails:

| Mode | Sampling limit |
| --- | --- |
| Architecture | Read top-level docs/config plus the smallest set of entry points and boundary files that explain ownership. |
| Convention | Compare 2-4 nearby or analogous files before naming a convention. |
| Feature Trace | Follow one primary happy path end to end, then mention important branches only if they affect comprehension. |
| Syntax/API | Explain only constructs visible in the target area; do not teach the full language or framework. |
| Testing | Inspect nearby tests and obvious test commands/config; do not run expensive test suites unless the user asks. |
| History | Use focused `git log`/`git blame` or provided PR/issue history for relevant paths only; do not infer rationale from silence. |

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
```

- [ ] **Step 2: Validate frontmatter fields**

Run:

```bash
sed -n '1,20p' Skills/catch-me-up/SKILL.md
```

Expected output begins with:

```text
---
name: catch-me-up
description: "Build a mental model
tools:
```

- [ ] **Step 3: Validate reference link**

Run:

```bash
rg "references/exploration-modes.md" Skills/catch-me-up/SKILL.md
test -f Skills/catch-me-up/references/exploration-modes.md
```

Expected: `rg` prints the linked reference path and `test` exits successfully.

- [ ] **Step 4: Commit skill body**

Run:

```bash
git add Skills/catch-me-up/SKILL.md
git commit -m "feat: add catch-me-up comprehension workflow"
```

Expected: commit succeeds with only the `SKILL.md` change.

### Task 4: Add Lightweight Validation

**Files:**
- Create: `Skills/catch-me-up/scripts/.gitkeep`

- [ ] **Step 1: Preserve empty scripts directory**

Run:

```bash
touch Skills/catch-me-up/scripts/.gitkeep
```

Expected: `.gitkeep` exists and no executable script is introduced.

- [ ] **Step 2: Validate required headings and guardrails**

Run:

```bash
rg "^## (Guardrails|Workflow|Output Contract|References)$" Skills/catch-me-up/SKILL.md
rg "Do not invent history" Skills/catch-me-up/SKILL.md
rg "This is a read-only comprehension skill" Skills/catch-me-up/SKILL.md
rg "Step 1: Determine Exploration Mode" Skills/catch-me-up/SKILL.md
rg "Depth guardrails" Skills/catch-me-up/SKILL.md
```

Expected: all commands print matches.

- [ ] **Step 3: Validate there are no planning placeholders**

Run:

```bash
if rg -n "T[B]D|T[O]DO|implement[ ]later|fill[ ]in[ ]details|Similar[ ]to[ ]Task" Skills/catch-me-up; then
  exit 1
else
  echo "No placeholders found"
fi
```

Expected:

```text
No placeholders found
```

- [ ] **Step 4: Commit validation marker**

Run:

```bash
git add Skills/catch-me-up/scripts/.gitkeep
git commit -m "chore: preserve catch-me-up scripts directory"
```

Expected: commit succeeds with only `.gitkeep`.

### Task 5: Smoke Test The Skill Against This Repo

**Files:**
- No file changes expected

- [ ] **Step 1: Run a manual trigger prompt in a fresh agent or session**

Prompt:

```text
Use the catch-me-up skill to orient me to the commit-message skill in this repo. Keep it concise.
```

Expected: the response uses the `catch-me-up` workflow, reads `Skills/catch-me-up/references/exploration-modes.md`, and analyzes `Skills/commit-message/SKILL.md`.

- [ ] **Step 2: Check output quality**

Expected response characteristics:
- includes evidence checked
- uses a table for the selected exploration modes
- chooses modes based on trigger fit instead of forcing all six
- cites `Skills/commit-message/SKILL.md`
- does not edit files
- does not invent test execution or history
- includes confidence gaps or next probes
- includes a diagram only if it clarifies the target area

- [ ] **Step 3: Patch wording if the smoke test reveals ambiguity**

If the agent treats the skill as a review or implementation instruction, confirm this sentence exists in `Skills/catch-me-up/SKILL.md`:

```markdown
This is a read-only comprehension skill. During this skill, do not edit files, produce review findings, fix bugs, stage changes, create commits, or publish pull requests unless the user separately asks for that work after the catch-up brief.
```

If the sentence exists and the smoke test still produces review findings, add this guardrail under `## Guardrails`:

```markdown
- Do not label concerns as findings, blockers, approvals, or requested changes during this skill. If concerns are useful for comprehension, label them as optional "things to inspect next".
```

- [ ] **Step 4: Commit smoke-test wording changes if needed**

Run only if Step 3 changed the file:

```bash
git add Skills/catch-me-up/SKILL.md
git commit -m "docs: tighten catch-me-up read-only guardrail"
```

Expected: commit succeeds only when the smoke test required a wording adjustment.

## Self-Review

- Spec coverage: the plan implements the six-mode framework, adds evidence rules, preserves local skill repo conventions, and includes validation.
- Placeholder scan: no plan step relies on placeholder tokens, vague future work, or unspecified test commands.
- Type consistency: file paths and skill name are consistently `Skills/catch-me-up`, `catch-me-up`, and `references/exploration-modes.md`.
