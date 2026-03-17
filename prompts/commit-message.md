# Commit Message Prompt

## Purpose
Generate a clear, conventional commit message from a diff or description of changes.

## Template

```
Generate a Git commit message for the following changes.

Follow the Conventional Commits specification (https://www.conventionalcommits.org):
  <type>(<scope>): <short description>

  [optional body]

  [optional footer]

Types: feat | fix | docs | style | refactor | perf | test | chore

Changes:
{{changes}}
```

## Variables
- `{{changes}}` – a description of the changes made, or a git diff

## Example Output
```
feat(auth): add JWT refresh token support

Implements automatic token refresh when the access token expires.
Adds a /auth/refresh endpoint and updates the middleware accordingly.

Closes #42
```
