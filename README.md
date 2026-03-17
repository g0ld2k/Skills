# Personal Agent Skills

Minimal personal repo for reusable agentic skills across projects.

## Structure

- `Skills/<skill-name>/SKILL.md` - skill instructions + workflow
- `Skills/<skill-name>/references/` - optional supporting notes
- `Skills/<skill-name>/scripts/` - optional helper scripts used by the skill
- `Skills/_template/` - starter template for new skills
- `scripts/new-skill.sh` - quick scaffold script for new skill folders

## Add a New Skill

### Option 1: Script (fast)

```bash
bash scripts/new-skill.sh my-skill "What this skill is for"
```

### Option 2: Manual

1. Copy `Skills/_template` to `Skills/<your-skill-name>`.
2. Update `SKILL.md` frontmatter and workflow.
3. Add any references or helper scripts if needed.

## Personal Checklist

Before using a skill regularly:

- title + description are specific
- guardrails are explicit (especially risky actions)
- workflow has deterministic steps
- output format is clear
- references are linked only when they add value

## Notes

- This repo is intentionally lightweight and personal-first.
- Keep skills practical and task-oriented rather than generic.
