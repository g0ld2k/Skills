# Testing Language Rules

## Core Rule

Never imply tests ran unless they were actually executed in the current session.

## Required Split

Always separate:

- `Tests Changed`: what test files/cases were modified.
- `Tests Run`: exact commands executed and their outcomes.

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
- Include one automated step if available.
