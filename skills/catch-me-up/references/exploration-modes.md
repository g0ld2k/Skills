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
