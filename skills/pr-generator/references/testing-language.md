# Testing Language Rules

## Core Rule

Never imply tests ran unless they were actually executed in the current session.

## Required Split

Always separate:

- `Tests Changed`: what test files/cases were modified.
- `Tests Run`: exact commands executed and their outcomes.

For the PR body's `Automated validation` field, use exactly one state:

- known command + run: record the exact command and its observed result;
- known command + not run: record the exact command plus the literal `Not run
  in this session`, with no result claim; or
- no known command: record the exact fallback `Automated validation: not available (no automated test command is known)`.

## Allowed Phrasing

Use these patterns:

- `Tests Changed: Added coverage for token refresh expiry paths in AuthServiceTests.`
- `Tests Run: swift test (pass).`
- `Tests Run: make test (failed: 2 failing tests in SyncEngineTests).`
- `Tests Run: Not run in this session.`

## Disallowed Phrasing

Do not use:

- `All tests pass` (unless command output confirms it in-session)
- `Verified` / `validated` without evidence
- inferred counts such as `+56 tests` unless directly supported by diff or output

## Manual Validation Guidance

For `How to Validate`:

- Write reproducible steps with expected outcomes.
- Prefer 2-5 steps focused on behavior changed in this PR.
- A known command may be included as a runnable automated step, even if it was
  not run in this session; in that case, give only the exact command to run and
  make no claim about its result.
