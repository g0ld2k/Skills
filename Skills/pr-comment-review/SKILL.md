---
name: pr-comment-review
description: Systematically review and respond to GitHub pull request comments. Fetches all review comments, analyzes each for validity and priority, recommends actions (code fixes vs explanatory replies), implements approved changes, runs tests, and posts responses with proper attribution. Use when asked to "review PR comments", "respond to PR review", or "address PR feedback".
allowed-tools: github-mcp-server-pull_request_read bash view edit grep glob ask_user update_todo create
metadata:
  author: user
  version: "1.0"
---

# PR Comment Review Skill

## Overview

This skill provides a systematic 4-phase workflow for handling GitHub pull request review comments:

1. **Fetch & Analyze** - Retrieve and assess all comments
2. **Present Recommendations** - Show prioritized action plan
3. **Implement Fixes** - Make code changes and run tests
4. **Post Responses** - Reply to each comment with attribution

## Workflow

### Phase 1: Fetch & Analyze

1. **Get PR Information**
   - Ask user for repository owner/name and PR number if not provided
   - Use `github-mcp-server-pull_request_read` to fetch:
     - `method: get` - PR metadata
     - `method: get_review_comments` - All review comment threads
     - `method: get_comments` - General issue comments

2. **Analyze Each Comment**
   For each review comment, determine:
   - **Validity**: Is the concern legitimate? (VALID/INVALID/PARTIAL)
   - **Priority**: Impact level (HIGH/MEDIUM/LOW)
   - **Action**: What to do (CODE FIX / REPLY ONLY / DISCUSS)
   - **Effort**: Time estimate for implementation

#### Priority Levels
- **HIGH**: Security issues, bugs, misleading claims, breaking changes
- **MEDIUM**: Code quality, test coverage, error handling, maintainability
- **LOW**: Style preferences, unclear/stale comments, minor optimizations

### Phase 2: Present Recommendations

Create a structured summary for user approval:

```markdown
## Comment #N - [File:Line] [Priority]
**Issue:** Brief description
**Validity:** VALID/INVALID with reasoning
**Recommendation:** FIX/REPLY/DISCUSS
**Action:** Specific steps to take
**Suggested Response:** Draft reply text
```

Group comments by action type (code fixes vs replies) and present summary table with:
- Comment number
- File and line reference
- Priority level
- Recommended action
- Estimated effort

Use `ask_user` to:
- Get approval on the plan
- Clarify ambiguous cases (e.g., multiple valid implementation approaches)
- Determine signature format preference for responses

### Phase 3: Implement Code Fixes

**ONLY proceed with user approval**

1. **Branch Strategy**
   - Ask user preference: same PR branch or new fix branch
   - Use `git checkout` to switch to appropriate branch

2. **Make Changes**
   - Use `view` to read relevant files
   - Use `edit` to make **surgical, minimal** changes
   - Address only what's needed for each comment
   - Avoid scope creep

3. **Validate Changes**
   - Run existing test suite (e.g., `make test`, `npm test`, etc.)
   - **CRITICAL**: Do not proceed if tests fail
   - Report test results clearly

4. **Commit & Push**
   - Commit with descriptive message referencing PR and topics
   - Example: `"Address PR #19 review comments - Fix WCAG claim, add error handling"`
   - Push to PR branch using `git push`

### Phase 4: Post Responses

1. **Get Comment IDs**
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pr}/comments --jq '.[] | .id'
   ```

2. **Post Each Reply**
   ```bash
   gh api -X POST repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies \
     -f body="Response text

   - [Signature]"
   ```

3. **Verify Posting**
   - Check for successful API responses
   - Report any failures immediately

## Response Guidelines

### Tone & Style
- **Acknowledge valid concerns**: "Good catch!" or "You're right"
- **Explain decisions**: "For this use case..." or "The rationale is..."
- **Request clarification**: "Could you clarify..." or "I don't see..."
- **Be concise**: Keep responses under 3-4 sentences
- **Be specific**: Avoid generic "will fix" - say what you did

### Signature Format
Always ask user for preferred signature. Common patterns:
- `- GitHub Copilot CLI`
- `- AI Assistant`
- Custom format specified by user

## Tool Usage

### GitHub API Tools
- **`github-mcp-server-pull_request_read`**: Fetch PR data
  - `method: get` - Get PR details
  - `method: get_review_comments` - Get review threads
  - `method: get_comments` - Get issue comments

### File Operations
- **`view`**: Read source files for context
- **`edit`**: Make surgical code changes
- **`grep`**: Search codebase for related code
- **`glob`**: Find files by pattern

### Git Operations (via bash)
```bash
git checkout <branch>           # Switch branches
git checkout -b <new-branch>    # Create fix branch
git add -A                      # Stage changes
git commit -m "message"         # Commit changes
git push origin <branch>        # Push to remote
```

### GitHub CLI (via bash)
```bash
# Get PR details
gh pr view <number> --repo <owner>/<repo>

# List review comments
gh api repos/<owner>/<repo>/pulls/<pr>/comments

# Post comment reply
gh api -X POST repos/<owner>/<repo>/pulls/<pr>/comments/<id>/replies \
  -f body="text"
```

### Session Management
- **`ask_user`**: Get approvals and clarifications
- **`update_todo`**: Track progress through 4 phases
- **`create`**: Make plan document in session workspace

## Edge Cases

### Stale/Invalid Comments
If comment references non-existent files/lines:
- Mark as INVALID in analysis
- Response: "I don't see [X] in the current code - could you clarify?"

### Conflicting Feedback
If multiple reviewers disagree:
- Mark as DISCUSS in analysis
- Ask user which direction to take

### Large Change Sets
If >10 comments or >1 hour estimated effort:
- Break into phases
- Get approval for each phase separately

### Test Failures
If tests fail after changes:
- **STOP immediately**
- Report failure details
- Do NOT post responses
- Fix tests or revert changes

## Example Session

**User:** "Review PR #19 comments"

**Agent Workflow:**

1. **Fetch** (Phase 1)
   - Get PR #19 from `g0ld2k/Zoner`
   - Found 6 review comments
   
2. **Analyze** (Phase 1)
   - Comment 1: WCAG claim - HIGH priority - FIX
   - Comment 2: Weak test - MEDIUM priority - FIX
   - Comment 3: Unused constants - LOW priority - REPLY (invalid)
   - Comment 4: Implementation approach - HIGH priority - REPLY (design choice)
   - Comment 5: Error handling - MEDIUM priority - FIX
   - Comment 6: Alpha bug - MEDIUM priority - FIX

3. **Present** (Phase 2)
   - Show 4 code fixes + 2 replies
   - Get user approval
   - Confirm signature: "- GitHub Copilot CLI"

4. **Implement** (Phase 3)
   - Make 4 surgical changes
   - Run tests: 110 passing ✓
   - Commit and push

5. **Respond** (Phase 4)
   - Post 6 responses with signature
   - Verify all posted successfully

**Output Summary:**
```
✅ Addressed 6 PR comments
✅ Made 4 code fixes
✅ All 110 tests passing
✅ Commit: abc1234
✅ PR: https://github.com/owner/repo/pull/19
```

## Common Pitfalls

- ❌ Don't post responses before implementing fixes
- ❌ Don't assume comment validity without checking code
- ❌ Don't make changes without running tests
- ❌ Don't use generic "will fix" responses
- ❌ Don't forget signature on responses
- ❌ Don't proceed if tests fail

## Output Format

Final summary must include:
- ✅ Total comments addressed
- ✅ Number of code fixes made
- ✅ Test results (X tests passing)
- ✅ Commit SHA and branch name
- ✅ PR URL for verification
