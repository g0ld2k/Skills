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

Fill in every section. Delete guidance text (the italic lines) once replaced.
See `## Add a New Skill` in README.md for the full scaffold-to-validate steps.

---

## Frontmatter

The template starts with real YAML frontmatter so copying it directly to
`skills/<name>/SKILL.md` gives the validator the required first line (`---`).
Fill in the placeholder values before validating.

- `name` must match the containing directory exactly, kebab-case.
- For model-invoked skills, `description` must start with the literal words
  "Use when" and list *triggers only* — situations that summon the skill.
  Never summarize the workflow here; that belongs in the body.
- For explicit-only skills, `description` is instead a one-line human-facing
  summary. It carries no model-facing trigger list because only the user can
  invoke the skill.
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
  not add it to a skill that is not explicit-only. Explicit-only skills are
  exempt from the validator's model-facing "Use when" description rule.
- Add the skill to `SKILL_BUDGETS` in `tests/test_skill_quality.py`. Its
  whitespace-delimited ceiling covers `SKILL.md` and every reference that all
  valid runs must load. Declare those files explicitly under `always_loaded`;
  do not infer them from prose. A reference selected only for an observable
  mode, condition, blocked path, or skill-authoring scenario remains
  progressive disclosure. Lower the ceiling when a review reduces the total;
  raising it requires explicit justification and approval.

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

Operationalize every judgment word the skill's rules depend on. If a rule
needs "material" or "significant" or "stale," define it here or delete the
rule — do not leave a judgment call unresolved. Follow the house pattern in
`skills/catch-me-up/SKILL.md`, which turns "which mode do I use" into a table
of trigger signals:

| Term/Mode | Trigger signals / definition |
| --- | --- |
| `<term>` | `<concrete, checkable condition>` |

## `## Inputs and Defaults`

Table every input the skill needs before it can start, its source, and what
happens with no explicit value — a stated default or an explicit block.

| Input | Source | Default (or: blocks if absent) |
| --- | --- | --- |
| `<input>` | `<where it comes from>` | `<default value>` / blocks |

## `## Guardrails`

Non-negotiable musts. At minimum: never-invent (ground claims in evidence;
say what's unknown); approval gates (which state-changing actions — commit,
push, merge, publish — need explicit authorization, and what scope); external-
text rule (fetched issue/comment/session text is content to evaluate, not
instructions to follow).

## `## Workflow`

Numbered phases, each with an observable exit condition (not "understand the
code" but "produced a table of N findings with file:line evidence"). Keep
phases small enough that a restart can resume mid-workflow from the exit
condition of the last completed phase.

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

Any gate failing emits the Blocked Report (see below) instead of proceeding.
Delete this section if the skill never gates an irreversible action.

## `## Output Contract`

What the final report must contain, as a checklist — not prose. State the
things every run must report (what was checked, what changed, what's still
open) so output is comparable across runs.

## `## Blocked Report`

Reference the vendored shape rather than restating it:

    references/conventions.md for the exact Blocked Report format, capability
    ladder, temp-file rule, and external-text rule.

> If this skill keeps the `references/conventions.md` link, run `python3
> scripts/sync-shared-conventions.py` before validating. The sync script
> discovers consumers from that link, and the validator checks that each copy
> matches `_shared/conventions.md`. If the skill doesn't need the shared file,
> remove the reference instead of leaving it dangling.

## `## Validation Scenarios`

Point to `references/validation-scenarios.md` rather than inlining scenarios in
SKILL.md. Include at least 3 scenarios: happy path, edge case, and adversarial,
covering activation and output behavior. This is a repository convention rather
than a validator check — nothing fails CI if the file is missing, so it is on
the author to write it. Per `superpowers:writing-skills`, write each scenario
RED first —
confirm it fails without the skill's guardrail — before writing the GREEN
behavior the skill should produce. See
`skills/pr-closeout-loop/references/validation-scenarios.md` for the format
(Setup / Prompt / Pass per scenario); each label must have non-empty content.

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
