---
name: pull-request
description: Use when writing a PR title or body, or opening or updating a PR.
license: MIT
metadata:
  forked-from:
    skill: pr
    author: Matt Pocock
    url: "https://github.com/mattpocock/skills"
  credits:
    skill: show-me
    author: Dex Horthy
    organisation: Humanlayer
    url: "https://github.com/humanlayer/skills/blob/main/plugins/show-me/skills/show-me/SKILL.md"
---

Forked from Matt Pocock's `pr` skill; see [CREDITS.md](CREDITS.md).

The title is a Conventional Commit subject: `type(scope): subject`, lowercase, no trailing period. Squash merges make it the commit subject on the default branch.

Use this template for writing the PR body:

```markdown
<one or two plain sentences: what changed and why>

## Summary

<brief explanation, with a visual when it clarifies the change>

## Evidence

- **Before:** <screenshot/output/failing test run>
  **After:** <screenshot/output/passing test run>

## Merge Danger

**Door:** <one-way or two-way>

<optional: description>

**Blast Radius:** <one-word description>

<optional: potential ramifications of merge>
```

## Sections

Skip all preambles and keep prose brief. Use the user's domain language from `GLOSSARY.md` when the repo has one.

### Opening sentences

Squash merges use the PR body as the commit message, and `testflight-notes` drafts release notes from those messages, so the opening sentences say in plain words what changed for the user and why.

### Summary

Use brief prose when it makes the change clear. For logic, structure, or
control flow that is harder to follow in prose, choose the smallest visual
that explains it. See [summary examples](references/summary-examples.md) for
pseudocode, trees, diagrams, and diff sketches.

### Evidence

Concrete evidence that the change works. Show a before and after.

For a logic change, show the relevant test as pseudocode and cite the observed test result or console output. Include both runs when you have failing and passing evidence.

For a UI change, use the project's launch instructions or build configuration to run the app. Capture the base revision in a temporary `git worktree`, then capture the branch on the same device with the same data.

Inspect the changed UI at the size people will see it and compare it with the supplied design reference when available. For an interactive change, perform the affected action and report what happened. In Evidence, describe what the screenshots show and identify any check you could not complete.

Keep the images out of the commit. Reference each in the PR body as `![alt](./after.png)`. For `gh pr create` or `gh pr edit`, pass the matching path with `--attach './after.png#alt text'` (gh 2.102 or later).

### Merge Danger

Describe whether it's a one-way or two-way door. You can walk back through two-way doors, but not one-way doors. A PR that is cheap to roll back is lower risk. Changes that involve destructive actions or hard-to-reverse decisions are one-way doors.

When the Door is one-way, add the `needs-human-verification` label (`--label needs-human-verification`); the maintainer removes it after checking by hand.

The blast radius is the potential impact or scope of the changes introduced by this PR. Consider all possibilities. Examples are layout shift, breakages for consumers, mobile responsiveness, etc.
