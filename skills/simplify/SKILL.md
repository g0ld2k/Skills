---
name: simplify
description: Review or simplify a specified code change for reuse, clarity, and avoidable work.
license: MIT
---

# Simplify

Review the requested diff or files for changes that reduce complexity without
unintended behavior changes. Use staged/unstaged diffs or an explicitly provided
base. If no diff exists, review only files named by the user or edited in this
task; otherwise report that scope is missing.

Inspect surrounding code when it helps verify a finding. Preserve file types:
show symlink targets without following them, describe binary changes without
printing bytes, and do not expose secret-bearing files or broad unrelated trees.
These boundaries apply to referenced-file fallback as well as changed files.

Look for existing utilities, redundant state, leaky abstractions, needless
indirection, repeated work, or unbounded resource use. Do not invent a new
abstraction merely to remove a small duplication. Separate demonstrated bugs
and material efficiency issues from optional style preferences.

Review a small diff directly. Delegate independent portions only when useful
and authorized; never require a fixed reviewer count. Combine overlapping
findings and cite concrete locations, impact, confidence and a proposed change.
Omit speculative findings or explain their uncertainty.

For review-only requests, return findings without edits. If the user asks for
cleanup, or has already selected a scope/policy, apply valid in-scope corrections
without another selection gate. Ask only when a consequential behavior change or
unclear scope requires a decision. Use numbered IDs when the user needs to select
among independent choices, not as a mandatory reporting format.

Preserve unrelated changes and requested behavior. Validate affected behavior
and repository-required checks; reuse unaffected successful verification.
Report what changed, meaningful deferred findings, and actual validation. This
skill does not authorize commits, pushes, messages, or merges.

When changing review scope or selection behavior, use the relevant
[validation scenarios](references/validation-scenarios.md).
