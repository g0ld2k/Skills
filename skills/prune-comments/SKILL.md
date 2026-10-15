---
name: prune-comments
description: Remove low-value code comments when the user requests comment cleanup or another workflow instructs it, preserving useful maintenance knowledge.
license: MIT
---

# Prune comments

Clean up existing comments using this test: **Does this give a future maintainer
useful information that is not readily apparent from the code?** Judge API
documentation from the caller's perspective, without assuming access to the
implementation. Length and whether a comment explains "what" or "why" are clues,
not verdicts.

## Select the target

Use the requested diff, staged or unstaged changes, or explicit files. Without a
target, inspect staged and unstaged changes plus untracked source files. If no
local changes exist, ask for a target before expanding scope.

For a branch, commit, or PR diff, resolve its base and head before editing.
Confirm that the editing checkout is at the selected head; otherwise use a
suitable checkout or report the mismatch without editing the current files.
Preserve local changes when choosing a checkout.

Report symlink targets without following or editing them. Apply this boundary
to automatic discovery, explicit targets, and contextual reads, including paths
that traverse symlinked directories.

For a diff, only touched comments are eligible for edits; a partially changed
multiline comment is eligible as a whole. Explicit files authorize inspecting
all their comments. For newly added source files, only comments present in the
selected version are eligible. A staged-only target selects index contents;
an unstaged-only target selects the working-tree diff against the index.
Read surrounding code and repository guidance as needed for evidence, while
keeping edits within the target. Reconcile staged and unstaged versions against
the current file before editing; preserve comments and other edits exclusive to
an unselected version, as well as staging state. If a selected comment cannot
be safely mapped to the current file, report it rather than overwrite the overlay.
Apply cleanup edits to the working tree, leaving index contents unchanged
unless the user explicitly requests staging; selecting a staged diff alone
identifies eligible comments without authorizing index writes.

Default to maintained project source, including tests and scripts. Skip
generated files, vendored dependencies, and copied third-party code unless the
user explicitly includes them; naming a containing directory or broad diff does
not itself override this exclusion.

## Evaluate each eligible comment

- **Restatement:** Remove narration of trivial code, such as `// Increment the
  counter` above `counter += 1`. Preserve explanations of complex or non-obvious
  behavior when they reduce the effort needed to understand it.
- **Durable rationale:** Preserve continuing constraints, external limitations,
  surprising behavior, and explanations that prevent plausible mistakes. Strip
  session history about who chose an approach or what was discussed. For
  example, replace a paragraph about deciding against webhooks with the useful
  constraint: `// This provider omits webhook events for deleted accounts.`
  Retain that claim only when supported by the original comment and context.
- **Contracts:** Preserve meaningful API information such as side effects,
  missing-value behavior, units, and concurrency requirements. Remove empty
  restatements where repository conventions permit, preserving required
  documentation structure.
- **Navigation:** Keep section headings and test labels that materially improve
  scanning. Remove labels that merely announce the next obvious statement.
  In a short test with one obvious setup, call, and assertion, remove
  `Arrange`/`Act`/`Assert` labels; conventional names alone do not establish
  navigation value.
- **Protected comments:** Preserve linter suppressions, compiler directives,
  generated-file markers, license notices, and annotations with tooling effects.
  Establishing that these are unnecessary belongs in a separate task.
- **Uncertain intent:** Investigate using available code and repository context.
  Preserve comments whose value remains uncertain. Remove TODOs and
  commented-out code only when repository evidence clearly establishes they are
  redundant or obsolete.
- **Contradictions:** Correct or remove misleading comments when intended
  behavior is established by repository evidence such as a documented contract,
  tests, or caller requirements. Agreement between a name and its implementation
  alone does not settle a conflicting comment. When the mismatch could indicate
  a code bug, preserve the comment and report the ambiguity rather than assuming
  the implementation is authoritative.

## Edit and verify

Delete comments that add no useful information. Where a comment mixes useful
knowledge with narration, rewrite it concisely while retaining the supported
meaning. Limit edits to existing comments and incidental whitespace needed for
their removal; executable code, symbol names, and broader refactoring remain
outside scope. Honor review-only requests by returning findings without edits.

Before editing, retain enough of the original state to distinguish this cleanup
from pre-existing changes. Review the resulting patch to confirm every edit is
within scope, executable code is unchanged, and protected comments remain
intact. Preserve syntax and behavior where comment placement is significant.
Run repository-required checks and relevant tooling checks when comment syntax
or documentation processing warrants them; reuse unaffected verification.

Finish once every eligible comment has been assessed and the cleanup patch has
been checked. Briefly report what was removed or tightened, actual validation,
and consequential unresolved cases. Keep individual edit justifications internal
unless requested. No edits is a valid result when no cleanup is justified.
