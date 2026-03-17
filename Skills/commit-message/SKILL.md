---
name: commit-message
description: "Generate concise, conventional commit messages based on staged changes and project context. Analyzes git diffs, CONTEXT.md updates, and change patterns to create well-formatted commit messages following conventional commit format. Use when asked to generate a commit message or prepare changes for commit."
tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Commit Message Generator

## Workflow

### 1) Collect context

Start by gathering information about the staged changes:

```bash
# List staged files
git --no-pager diff --cached --name-only

# Get change statistics
git --no-pager diff --cached --stat

# Review full diff if needed for complex changes
git --no-pager diff --cached
```

### 2) Read project context

If the repository has a `CONTEXT.md` file:
- Read the latest session history entries
- Identify the current phase or feature being worked on
- Note any architectural decisions or patterns mentioned
- Look for related documentation (PRD.md, TASKS.md, etc.)

### 3) Analyze the changes

Identify the commit type and scope:

**Commit types** (conventional commits):
- `feat:` - New feature or functionality
- `fix:` - Bug fix
- `refactor:` - Code restructuring without behavior change
- `perf:` - Performance improvement
- `docs:` - Documentation only
- `test:` - Adding or updating tests
- `chore:` - Build, tooling, dependencies
- `style:` - Formatting, whitespace (not visual style changes)

**Key questions**:
- What is the primary purpose of these changes?
- What components/models/views were affected?
- Are there breaking changes? (add `!` after type)
- What's the user-facing impact?

### 4) Generate commit message

Create a structured message following this format:

```
<type>[optional scope]: <short description>

<optional body>

<optional footer>
```

**Guidelines**:
- **Subject line**: 50-72 characters, imperative mood ("add" not "added")
- **Body**: Explain what and why (not how), wrap at 72 characters
- **Footer**: Reference issues, note breaking changes, mention closed phases

**Example structure**:
```
feat: add working hours to teams and teammates

Adds optional working hours to Team and Teammate models with precedence
logic: teammate > team > location. When a teammate belongs to multiple
teams, working hours are computed as the intersection of all teams.

Key changes:
- Added workingHoursStart/End to Team and Teammate models
- Introduced effective working hours precedence in AvailabilityState
- Updated Add/Edit Team and Add/Edit Teammate flows with working hours editor
- People tab rows now show availability based on effective hours
- Added 56 new unit tests for effective hours logic

Closes Phase 7 working hours enhancement.
```

### 5) Present for review

**Important**: Do NOT commit automatically. Present the generated message and wait for explicit approval:

```
Here's a suggested commit message:

<show formatted message>

Ready to commit when you confirm.
```

### 6) Commit only when approved

When the user explicitly says to commit (e.g., "commit it", "looks good", "please commit"):

```bash
git commit -m "<subject line>

<body>

<footer>"
```

## Best Practices

### Message quality
- Focus on the "what" and "why", not implementation details
- Group related changes into bullet points
- Mention test coverage additions
- Reference phase/milestone completion when applicable
- Keep language clear and concise

### Context awareness
- Use terminology from CONTEXT.md and PRD.md
- Reference architectural decisions when relevant
- Note if changes update documentation
- Mention platform-specific changes (iOS/macOS)

### Common patterns

**Feature additions**:
```
feat(scope): add <feature>

Brief description of what the feature does.

Key changes:
- Component/file changes
- New models or views
- Test coverage added

Closes <issue/phase>.
```

**Bug fixes**:
```
fix(scope): resolve <issue>

Explains what was broken and how it's fixed.

Changes:
- What was modified
- Edge cases handled

Fixes #<issue-number>.
```

**Refactoring**:
```
refactor(scope): extract <component>

Why the refactor improves the code.

Changes:
- Files affected
- Pattern introduced
- No behavior change
```

## Anti-patterns

❌ **Don't**:
- Use vague messages like "fix stuff" or "updates"
- Include implementation details in subject line
- Forget to mention breaking changes
- Commit without user approval
- Skip the body for non-trivial changes
- Use past tense ("added" instead of "add")

✅ **Do**:
- Keep subject line under 72 characters
- Use imperative mood
- Reference relevant issues/phases
- Include test coverage information
- Wait for explicit approval before committing
- Provide context from CONTEXT.md when available

## Example interactions

### Simple feature
**User**: "Generate a commit message for these staged changes"

**Assistant**:
1. Reviews `git diff --cached --stat`
2. Reads CONTEXT.md for current phase
3. Generates message following conventional format
4. Presents message and waits for approval

### Complex multi-file change
**User**: "Create a commit message"

**Assistant**:
1. Reviews full diff for understanding
2. Identifies primary change type and affected components
3. Groups related changes into bullet points
4. Includes test count and phase reference
5. Waits for "commit it" confirmation

### Documentation update
**User**: "Commit message for docs"

**Assistant**:
```
docs: update CONTEXT.md with Phase 7 completion

Documents team and teammate working hours implementation with
precedence logic and multi-team intersection behavior.
```
