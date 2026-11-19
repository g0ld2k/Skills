# Authoring a skill

Use the built-in skill-creator guidance. Lead with the outcome and what a
reviewer can inspect to tell whether it meets the request. Add domain context,
output preferences, and non-obvious constraints where they change the result.

```markdown
---
name: skill-name
description: Describe the specific task and when this skill applies.
license: MIT
---

# Skill title

State the outcome, observable completion criteria, and authority boundaries.
Name the evidence to report when a check is blocked. Link supporting details
at the decision that needs them.
```

For this repository, add `agents/openai.yaml` with a display name, a 25–64
character short description, and a default prompt mentioning `$skill-name`.
Give the default prompt a concrete result and the most useful review criterion.
For example, replace “Review these tests” with “Use `$test-adequacy-review`
to review the current changes for weak tests and coverage gaps. For each gap,
name a plausible regression the tests would miss and the assertion that would
catch it.”

Leave reasoning effort to the task and client. Describe where the work needs
to be exhaustive. When independent work regularly improves a skill, give the
host a concrete trigger for delegation and the boundaries the agents share.

Preserve the existing invocation policy when editing a skill. Only make a skill
explicit-only when requested; list it in `EXPLICIT_ONLY_SKILLS` and use both
Claude's `disable-model-invocation: true` frontmatter and Codex's
`policy.allow_implicit_invocation: false` metadata.

Do not require a literal description prefix, arbitrary word ceiling, gate table,
ledger, number of reviewers, or fixed output headings. Descriptions should be
short and discriminate the actual task from adjacent work. Separate real safety
and repository requirements from optional preferences. User intent and existing
scope override workflow defaults.

Inspect callers before removing resources. Keep each installable skill
self-contained. If shared conventions are useful, link
`references/conventions.md` from the entrypoint; the sync script vendors the
canonical `_shared/conventions.md` and CI checks drift. Do not add another router
or script when ordinary instructions and existing tools suffice.

Validate structure with `python3 scripts/validate-skills-repo.py`, update affected
behavioral scenarios, and follow [evaluation guidance](eval.md). Test observable
results and safety boundaries; avoid tests of exact prose or headings.

## Official guidance

- [Prompting GPT-6.2 in Codex](https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra)
- [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Plugin skills](https://developers.openai.com/plugins/build/skills)
