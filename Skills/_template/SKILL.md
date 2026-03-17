---
name: your-skill-name
description: One-line summary of what this skill does and when to use it.
tools:
  - bash
  - view
  - edit
  - grep
  - glob
---

# Your Skill Name

## When to Use

Use this skill when:
- [scenario 1]
- [scenario 2]

## Guardrails

- Never [unsafe action] without explicit confirmation.
- Do not invent outputs, test results, or external state.

## Workflow

### Phase 0: Preflight

Run quick validation commands and stop on hard blockers.

### Phase 1: Gather Evidence

Collect only the context needed for the task.

### Phase 2: Execute

Perform deterministic steps in order.

### Phase 3: Validate

Run checks/tests where applicable and report exact outcomes.

### Phase 4: Output

Return concise results with any next actions.

## Output Contract

When finished, include:
1. Summary of what changed
2. Validation results
3. Risks or follow-up items

## References

- `references/` for optional supporting docs
