#!/usr/bin/env bash
set -euo pipefail

if [[ ${1:-} == "" ]]; then
  echo "Usage: $0 <skill-name> [description]" >&2
  exit 1
fi

name="$1"
description="${2:-Personal skill scaffold}"
root="Skills/$name"

if [[ -e "$root" ]]; then
  echo "Skill already exists: $root" >&2
  exit 1
fi

mkdir -p "$root/references" "$root/scripts"

cat > "$root/SKILL.md" <<EOF2
---
name: $name
description: $description
tools:
  - bash
  - view
  - edit
  - grep
  - glob
---

# ${name}

## When to Use

Use this skill when:
- 

## Guardrails

- Never perform destructive operations without explicit confirmation.
- Do not claim work was done unless it was executed.

## Workflow

### Phase 0: Preflight

### Phase 1: Gather Context

### Phase 2: Execute

### Phase 3: Validate

## Output Contract

1. What changed
2. Validation performed
3. Follow-ups
EOF2

echo "Created: $root"
