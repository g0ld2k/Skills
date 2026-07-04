# PR Style Guide

## Principles

- Optimize for fast reviewer scanning.
- Prefer user-impact and behavioral outcomes over implementation trivia.
- Keep claims evidence-based from git diff and executed commands.

## Length Targets

- Title: ideally <= 72 chars.
- Goal: 1-2 sentences.
- What Changed: 3-7 bullets.
- Full body: usually readable in under 1 minute.

## Writing Rules

- Use concrete nouns (`SessionManager`, `SettingsView`) over vague terms (`logic`, `stuff`).
- Mention "why" once in Goal and "what" in bullets.
- Do not paste large code snippets into PR body.
- Avoid repeating data already visible in GitHub UI unless it adds context.

## Required Sections

- `Goal`
- `What Changed`
- `Testing`
- `Files Changed`
- `Risks / Breaking Changes`
- `How to Validate`

## Optional Sections

- `Notes` (milestones, linked issues, follow-ups)
- `Screenshots` (for visible UI changes)
- `Rollback / Mitigation` (include when operationally relevant)

## Category Vocabulary

Use consistent labels:
- `API`
- `Models`
- `UI`
- `Business Logic`
- `Data`
- `Infra/Config`
- `Docs`
- `Testing`
- `Performance`
- `Security`
