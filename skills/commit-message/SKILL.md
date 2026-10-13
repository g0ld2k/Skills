---
name: commit-message
description: Draft a Conventional Commit message from staged changes; commit them only when requested.
license: MIT
---

# Commit message

Inspect the staged diff and describe only those changes. An empty index is a
missing input, not permission to stage files. Use nearby history or project
terminology only when it helps resolve type or scope.

Prefer `<type>(optional-scope): <specific imperative subject>`; omit scope when
no area dominates. `style` means formatting, not a visual redesign. Explain
non-obvious intent or breaking impact in the body; add a breaking marker/footer
only when supported. A short subject and roughly 72-column wrapping are style
preferences, not reasons to change the requested content.

Return the message. Do not require a rationale unless the choice needs explaining.
A message request alone never stages, commits, or pushes. When the user or trusted
caller requests a commit and its existing authorization covers the staged work,
show the message and proceed without another approval question.

Before committing, recheck the staged scope and current branch so the message
still describes the authorized work. Reconcile unexpected changes before writing.
Use ordinary `git commit`, preserving hooks and signing; do not replace Git's
lifecycle with manual locks or commit plumbing. Confirm the resulting SHA and
subject, and report hook/validation failures honestly. A commit does not authorize
a push.

Use [shared conventions](references/conventions.md) for permission, verification,
and temporary-file handling. When changing this contract, exercise the affected
[validation scenarios](references/validation-scenarios.md).
