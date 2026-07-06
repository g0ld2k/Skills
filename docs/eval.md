# Smoke Evaluation Protocol

## Overview

The smoke evaluation protocol validates skills before deployment by running primary scenarios in a controlled environment. This ensures that:
- All Output Contract fields are present in the skill's response
- No gated action fires without its corresponding gate being satisfied

## Scope

For each skill that includes a `references/validation-scenarios.md` file, run the primary scenario with a fresh subagent (weakest available model) inside a fixture repo.

## Fixture Repository

Use `scripts/make-fixture-repo.sh` to create a deterministic fixture repository. The script:
- Initializes a git repo with pinned author/committer dates for reproducible commit hashes
- Creates a realistic project structure with Swift sources and tests
- Produces exactly 4 commits with a `build-1` tag at commit 3
- Leaves one staged, uncommitted change (modified `Sources/App/Session.swift`)

This fixture is suitable for scenarios involving commit messages, code review, dependency analysis, and change generation.

## Validation Steps

For each skill with validation scenarios:

1. **Read the validation scenarios.** Identify the primary scenario (typically Scenario 1 or marked as such).
2. **Create a fixture repo** by running `scripts/make-fixture-repo.sh` and capturing its path.
3. **Spawn a subagent** with the weakest available model (e.g., Haiku) to run the skill with the primary scenario prompt inside the fixture repo.
4. **Check Output Contract.** Verify that all required fields from the skill's output contract are present in the response.
5. **Check gated actions.** Verify that no gated action (as defined in the skill's gate schema) fired without its gate condition being satisfied.
6. **Record results.** Document pass/fail and any issues in the PR that modifies the skill.

## Output Contract Verification

Each skill defines an output contract specifying required fields and their schemas. The validation must confirm:
- All required fields are present
- No additional unexpected fields indicate incomplete implementation
- Field values conform to their declared types and constraints

## Gated Action Verification

Gated actions are tool calls or side effects that require a gate (e.g., merge approval, fresh green checks) before execution. The validation must confirm:
- Gates are checked before the corresponding action fires
- No action bypasses its gate condition
- The gate condition is evaluated with current, authoritative state (not stale assumptions)

## Documentation

Skills that pass evaluation should be noted in the PR description with a checkmark and the model used (e.g., "Haiku 4.5"). Skills that fail should list the specific Output Contract or gate violations and include guidance for remediation.
