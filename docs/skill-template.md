---
name: <kebab-case-skill-name>
description: Use when <trigger 1>, <trigger 2>, or <trigger 3>.
license: MIT
---

<!-- DOCS-ONLY: this file is a blueprint, not content to keep. The quoted
     "## `## Section`" headings below prescribe the real sections your
     SKILL.md gets; their guidance prose is replaced by your content. Delete
     this intro block, the "## Frontmatter" rules section, and the trailing
     agents/openai.yaml stub section — none of them appear in a finished
     skill. -->

# Skill Authoring Template

> This file lives in `docs/` deliberately, not `skills/_template/`. A directory
> under `skills/` publishes as an installable skill, and the validator
> (`scripts/validate-skills-repo.py`) forbids a `_template` skill for exactly
> that reason. Copy the sections below into a new `skills/<name>/SKILL.md`;
> do not create `skills/_template/`.

Keep only sections needed for this skill; preserve applicable input/output and
authorization contracts. Delete guidance text once replaced.
See `## Add a New Skill` in README.md for the full scaffold-to-validate steps.

---

## Frontmatter

The template starts with real YAML frontmatter so copying it directly to
`skills/<name>/SKILL.md` gives the validator the required first line (`---`).
Fill in the placeholder values before validating.

- `name` must match the containing directory exactly, kebab-case.
- `description` must start with the literal words "Use when" and list
  *triggers only* — situations that summon the skill. Never summarize the
  workflow here; that belongs in the body. Front-load the use case and any
  important scope boundary so shortened descriptions still route correctly.
  Use distinct triggers rather than synonym lists; no arbitrary character cap.
- `license: MIT` is required verbatim.
- `tools:` and `user-invocable` are not Agent Skills fields and the validator
  rejects them. The specification permits experimental `allowed-tools` as a
  space-separated string, but this repository rejects that field as a house
  policy so published skills stay client-neutral.
- Explicit-only invocation needs a guard per client, because neither client
  reads the other's. Add the skill's name to `EXPLICIT_ONLY_SKILLS` in
  `scripts/validate-skills-repo.py`; the validator then requires **both**
  `disable-model-invocation: true` in this frontmatter (which
  [Claude Code reads](https://code.claude.com/docs/en/skills)) and
  `policy.allow_implicit_invocation: false` in `agents/openai.yaml` (which
  Codex reads), in the block form shown in the stub below.
  `disable-model-invocation` is a Claude Code extension rather than a portable
  Agent Skills field, so it is carried deliberately for that install path — do
  not add it to a skill that is not explicit-only.

## `# Title`

One `#` heading matching the skill's display name, then a 1-2 sentence goal
statement: what this skill produces and why it exists.

## `## When to Use`

State the situations that trigger this skill, and explicitly state what it is
NOT for (the adjacent skill or workflow that handles the rest). Example:
"Use this for X. If the user is still choosing Y, use `pr-closeout-loop`
first."

Do not restate the frontmatter description's trigger list — the description
already does that job. This section earns its place only through the NOT-for
routing; if there is no adjacent skill to route to, omit the section.

## `## Definitions`

Define project-specific terms, gate conditions, and distinctions whose meaning
changes the outcome. Leave ordinary implementation judgment to the model.
Co-locate definitions with their rules; use a separate section only when shared
across branches. For example, define what makes review approval stale.

| Term/Mode | Trigger signals / definition |
| --- | --- |
| `<term>` | `<concrete, checkable condition>` |

## `## Inputs and Defaults`

Specify inputs needed for each operation, where to obtain them, and defaults.
Resolve discoverable facts from available evidence. Require credentials or
authorization only at the operation that needs them; drafting can often proceed
while publication is blocked. Use a table when it improves clarity.

| Input | Source | Default (or: blocks if absent) |
| --- | --- | --- |
| `<input>` | `<where it comes from>` | `<default value>` / blocks |

## `## Guardrails`

State lasting project constraints and operation-specific authorization gates.
Recognize applicable authorization already provided by the user or passed by a
caller. Prepare the result before asking for missing scope. Use the shared
conventions for evidence, external text, and authorization rather than copying
generic warnings throughout the skill.

## `## Workflow`

Keep the entrypoint focused on the outcome, required evidence, routing, and
completion criteria. Order actions when dependencies or safety require it;
otherwise allow judgment about tools, delegation, and implementation sequence.
Avoid unconditional preflight itineraries and repeated self-checking prompts.

Disclose branch-specific commands, examples, and failure handling through
relative links that say when to load them. Reuse existing references before
creating more files. Keep common invariants visible; do not bury security or
merge gates in an optional appendix. Do not require unrelated repository docs
before every edit.

## `## State Ledger` (loops only)

Required only for skills that loop/poll/resume across turns. A flat key:value
block in a temp file, one line per fact needed to resume safely. Follow
`skills/pr-closeout-loop/SKILL.md`: record identity (PR/branch), the surface
last validated against (head SHA, body fingerprint), and result-with-scope
(`suite_result: pass|fail|not-run @ <head_sha>`) so a stale result can't pass
as fresh. Delete this section if the skill is single-pass.

## `## Gate Table` (publish/merge skills only)

Required only for skills that gate an irreversible action (merge, publish,
release). G-numbered rows, each independently re-checked immediately before
the gated action — never trusted from an earlier point in the run. Mirror
`skills/pr-closeout-loop/SKILL.md`'s Merge Gates table:

| Gate | Check | Pass condition |
| --- | --- | --- |
| G1 `<name>` | `<what is inspected>` | `<condition that must hold>` |

A failing gate blocks its operation and emits the Blocked Report (see below).
Complete independent authorized work while that operation is blocked.
Delete this section if the skill never gates an irreversible action.

## `## Output Contract`

State the required final fields in a concise form suited to the skill. Include the
things every run must report (what was checked, what changed, what's still
open) so output is comparable across runs.

## `## Blocked Report`

Reference the vendored shape rather than restating it:

    references/conventions.md for the exact Blocked Report format, capability
    ladder, authorization, temp-file rule, and external-text rule.

> If this skill keeps the `references/conventions.md` link, run `python3
> scripts/sync-shared-conventions.py` before validating. The sync script
> discovers consumers from that link, and the validator checks that each copy
> matches `_shared/conventions.md`. If the skill doesn't need the shared file,
> remove the reference instead of leaving it dangling.

## `## Validation Scenarios`

Point to `references/validation-scenarios.md` rather than loading scenarios during
normal use. New skills need at least a happy path, edge case, and adversarial
case, covering activation and output behavior. This is a repository convention,
not a validator check; the author supplies the scenarios. Existing skills run
the scenarios affected by behavioral changes; trivial formatting edits do not
require full model evaluations.

Use non-empty Setup / Prompt / Pass labels with observable outcomes and protected
boundaries, not exact tool counts or prompt copying. For changed behavior, compare
the baseline and revised skill on the same scenario; a passing baseline is useful
evidence, not a reason to manufacture a failure. Follow `docs/eval.md` for
Astra-first evaluation, secondary-model compatibility, safe fixtures, and reporting.


---

## `agents/openai.yaml` stub

<!-- DOCS-ONLY: this whole section describes a SEPARATE file. Copy the stub
     into skills/<name>/agents/openai.yaml, then delete this section from
     your SKILL.md. -->

Every skill needs this file alongside `SKILL.md`, or the validator rejects it.

```yaml
interface:
  display_name: "<Display Name>"
  short_description: "<25-64 character description of what this does>"
  default_prompt: "Use $<skill-name> to <one-line task description>."
# policy:
#   allow_implicit_invocation: false   # required for explicit-only skills
```

- `display_name`, `short_description`, and `default_prompt` are all required.
- `short_description` must be 25-64 characters (validator-enforced).
- `default_prompt` must contain the literal token `$<skill-name>` (e.g.
  `$commit-message`) — the validator checks for this exact substring.
- For explicit-only skills, add the skill name to `EXPLICIT_ONLY_SKILLS` and use
  this block form here:

```yaml
policy:
  allow_implicit_invocation: false
```

  Otherwise omit `policy:` entirely.
