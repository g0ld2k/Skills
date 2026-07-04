# Title Heuristics

## Format

Use Conventional Commit format:

`<type>(optional-scope): <subject>`

Examples:
- `feat(auth): add refresh token rotation`
- `fix(sync): prevent duplicate CloudKit replay`
- `docs(readme): clarify local setup prerequisites`

## Type Selection

- `feat`: net-new user-facing capability.
- `fix`: behavior correction or bug resolution.
- `refactor`: structure changes without behavior change.
- `perf`: measurable performance improvement.
- `docs`: documentation-only changes.
- `test`: tests only.
- `build`: build/dependency/build-system changes.
- `ci`: CI pipeline/workflow changes.
- `chore`: maintenance that does not fit above.

## Scope Selection

- Include scope when a single subsystem dominates (for example `auth`, `ui`, `sync`).
- Omit scope if changes are broad and no single area dominates.

## Subject Rules

- Use imperative mood (`add`, `fix`, `improve`).
- Be specific and searchable.
- Avoid trailing punctuation.
- Avoid vague subjects like `update stuff`.

## Breaking Change

If clearly breaking, use `!` and note impact in PR body:
- `feat(api)!: remove v1 session endpoint`
