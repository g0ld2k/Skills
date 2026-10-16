---
name: commit-message
description: Use when drafting a Conventional Commit message, including within an authorized commit workflow.
license: MIT
---

# Commit Message

Generate a commit message for a clearly identified change. Staging and committing
belong to the user or calling workflow; this skill performs neither.

## Source

- Use staged changes by default. Inspect the full staged diff and file summary.
- If the user or calling workflow explicitly identifies another source (a supplied
  diff, commit range, or set of changes), inspect that source instead.
- If nothing is staged and no source is identified, report that and ask which
  changes to describe. Leave the working tree and index unchanged.
- Ground claims in the selected changes and supplied context. Use repository
  guidance, terminology, branch names, and history as context, not proof of changes.
  Mention only changes within the selected source. Claim test execution or results
  only when directly observed or supplied; adding tests does not prove they passed.
  Include issue IDs only when provided by the user or repository context.

## Message Standards

```text
<type>[optional scope][!]: <short description>

<optional body>

<optional footer>
```

- Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`,
  `chore`, `style`, `revert`. The `style` type covers formatting or whitespace.
- Scope: use a repository area when one clearly dominates; omit for mixed areas.
  Use terminology established by the repository or user.
- Subject: imperative mood, aiming for 72 characters or fewer. Short changes
  deserve short subjects.
- Body: include when it adds useful what/why context; wrap at about 72 characters.
- Breaking changes: mark clearly breaking changes with `!` before the colon and
  add `BREAKING CHANGE: <impact>` in the footer.

## Output

Return only the complete message in one code block. Explain choices only when
asked. If the source is missing or cannot be inspected, report the issue instead
of inventing a message.

Use [validation scenarios](references/validation-scenarios.md) when changing this
contract.
