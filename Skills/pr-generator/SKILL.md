---
name: pr-generator
description: "Generate comprehensive GitHub pull request descriptions by analyzing branch changes, commits, and test coverage. Creates concise PR descriptions with goal, changes, testing instructions, and files summary. Always presents for review before publishing."
tools:
  - bash
  - view
  - git
  - gh
  - grep
  - glob
---

# Pull Request Generator

## Workflow

### 1) Verify branch and changes

Start by collecting branch information:

```bash
# Get current branch name
git --no-pager branch --show-current

# Get commits ahead of main/master
git --no-pager log origin/main..HEAD --oneline 2>/dev/null || git --no-pager log origin/master..HEAD --online

# Get diff statistics
git --no-pager diff origin/main...HEAD --stat 2>/dev/null || git --no-pager diff origin/master...HEAD --stat
```

**Stop if**:
- Not on a feature branch (still on main/master)
- No commits ahead of base branch
- No file changes detected

### 2) Analyze commits and changes

Review the commit messages to understand the scope:

```bash
# Get detailed commit information
git --no-pager show --stat HEAD

# If multiple commits, review them all
git --no-pager log --pretty=format:"%h %s" origin/main..HEAD
```

**Extract**:
- Primary goal/purpose from commit messages
- Which models/views/services were modified
- Whether tests were added/updated
- Documentation changes

### 3) Check project context

If available, read relevant project files:
- `CONTEXT.md` - Current phase, recent decisions
- `PRD.md` - Phase information, feature descriptions
- `TASKS.md` - Task completion status

This helps frame the PR in terms of project milestones.

### 4) Identify test coverage

Look for test file changes:

```bash
# Check for test additions in the diff
git --no-pager diff origin/main...HEAD --stat | grep -i test
```

Count new tests if applicable:
- Unit tests added
- Integration tests added
- UI tests added

### 5) Generate PR description

Create a concise, structured PR description following this template:

```markdown
### Goal
[1-2 sentences describing what this PR accomplishes and why]

### What Changed
- **[Category]:** [Brief description of changes]
- **[Category]:** [Brief description of changes]
- **Testing:** [Test additions/coverage]

### Files Changed
[X files, +Y/-Z lines]

### How to Test
1. **[Test scenario 1]:** [Expected behavior]
2. **[Test scenario 2]:** [Expected behavior]
3. **Run tests:** `make test` or equivalent

### Notes
[Any additional context, phase completion, breaking changes, or follow-up work]
```

**Categories to use**:
- Models
- Views/UI
- Services/Business Logic
- Configuration
- Documentation
- Testing
- Performance
- Availability Logic (for availability-related changes)

**Guidelines**:
- Keep the goal concise (1-2 sentences max)
- Use bullet points with bold category labels
- Include specific file/class names when relevant
- Provide practical test scenarios users can follow
- Mention phase completion if from PRD.md
- Total description should be scannable in ~30 seconds

### 6) Present for review

**Important**: Always show the generated PR description to the user and explicitly ask for approval before publishing.

Say something like:
> "Here's the PR description. Does this look good, or would you like me to adjust anything before publishing?"

Wait for explicit approval (e.g., "looks good", "publish it", "go ahead").

### 7) Publish to GitHub

Only after receiving approval:

```bash
# First, push the branch if not already pushed
git push -u origin $(git branch --show-current)

# Then create the PR using gh CLI
gh pr create \
  --title "[conventional commit format title]" \
  --body "[generated description]" \
  --base main \
  --head $(git branch --show-current)
```

**Title format**: Use conventional commit format (e.g., `feat: Add working hours to teams`)

**On success**:
- Show the PR URL
- Confirm publication

**On failure**:
- Check if branch is already pushed
- Verify gh CLI is authenticated
- Provide helpful error message

## Best Practices

### Conciseness
- Avoid verbose explanations
- Focus on what changed and why
- Skip obvious details (e.g., "added a file" when the file list shows it)

### Structure
- Always use the template structure
- Bold important terms for scannability
- Use consistent category labels

### Testing section
- Provide manual testing steps where applicable
- Include automated test commands
- Note expected outcomes

### Context awareness
- Reference phase completion from PRD.md
- Mention related issues/PRs if relevant
- Flag breaking changes prominently

## Examples

### Good PR Description

```markdown
### Goal
Enable working hours support at both team and teammate levels with intelligent precedence logic: teammate-specific hours override team hours, which override location-based hours.

### What Changed
- **Models:** Added optional `workingHoursStart` and `workingHoursEnd` to `Team` and `Teammate`
- **Availability Logic:** Enhanced `AvailabilityState` with effective working hours precedence
- **UI Updates:** Working hours editor integrated into Add/Edit flows
- **Testing:** Added 56 new unit tests covering precedence scenarios

### Files Changed
15 files, +432/-92 lines

### How to Test
1. **Single team hours:** Create team with hours, add teammate, verify availability
2. **Teammate override:** Set custom teammate hours, verify precedence
3. **Run tests:** `make test` - all 56 new tests should pass

### Notes
Completes Phase 7 working hours enhancement.
```

### Bad PR Description (too verbose)

```markdown
### Goal
This pull request adds the ability for users to set working hours on teams and also on individual teammates. The system will use a precedence hierarchy to determine which working hours apply. If a teammate has their own hours set, those will be used. Otherwise, if they belong to a team with hours, the team's hours will be used. And if they belong to multiple teams, we calculate the intersection of all the team hours. This is important because it gives users flexibility...

[Rest is too long and rambling]
```

## Anti-patterns

❌ **Don't**:
- Write verbose paragraphs instead of bullets
- Include implementation details better suited for code comments
- List every single file changed (use summary stats)
- Create the PR without user approval
- Skip the testing section
- Use vague category labels

✅ **Do**:
- Keep it scannable and concise
- Focus on user-facing changes and impacts
- Provide practical testing instructions
- Always get explicit approval before publishing
- Use consistent formatting and structure
- Reference project documentation when relevant
