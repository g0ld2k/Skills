# Publishing a PR

Load only for a requested create/update operation. The authorization gate in
SKILL.md applies to both CLI and MCP paths. Resolve helper paths relative to
this skill directory; run Git operations in the target repository.

## Establish Live Publication State

Confirm repository, head, base, commits ahead, and changed files. Do not publish
from the repository default branch. An authorized protected non-default head is
allowed; respect its actual push rules and never bypass protection. Fetch current
remote state before publication, and reconcile any difference from the draft
before writing. Preserve an explicitly provided base, including integration and
stacked-PR bases.

Prefer an available authenticated `gh` capability; otherwise use an authenticated
GitHub MCP equivalent. Check authentication only as needed to select a working
capability. If neither can publish, return the draft and the blocked operation.

Look up the current branch's open PR to choose create or update. A lookup error
is not evidence that no PR exists. Confirm a definitive not-found result before
creating, and surface a base mismatch rather than silently retargeting a PR.

## CLI

Examples assume branch/base and any existing PR number have been verified.

```bash
gh pr view "$BRANCH" --json number,url,title,baseRefName
```

Use a unique temporary file for the complete body:

```bash
pr_body_file="$(mktemp "${TMPDIR:-/tmp}/pr-body.XXXXXX")"
cat > "$pr_body_file" <<'MD'
<generated markdown body>
MD
```

For an existing PR, update its title/body:

```bash
gh pr edit <number> --title "<title>" --body-file "$pr_body_file"
```

For a new PR, resolve the destination repository and head ref explicitly; do not
assume a remote named origin is the intended destination. Push only with covered
authority, using an ordinary fast-forward push for create and update alike.
If the remote ref already exists, inspect its relationship before pushing;
a PR-create request never authorizes replacing another branch's history. Do not
escalate a rejection to force-with-lease without separate rewrite authority.

With the example's origin verified as that destination, create using the chosen
base and head (add `--draft` when a draft was requested):

```bash
git push -u origin "$BRANCH"
gh pr create --title "<title>" --body-file "$pr_body_file" \
  --base "$BASE_BRANCH" --head "$BRANCH"
```

## MCP

Use available MCP tools to resolve repository/head/base, inspect existing PRs,
and create or update the requested title/body. Apply the same evidence and
authorization gates. If a branch push is needed, use an available authorized
push capability; PR creation permission alone does not authorize that push.

## Result

Confirm the resulting PR URL, title, base, and head. On failure, read
[failure handling](failure-handling.md), retain the draft, and report the failed
operation. Clean up temporary working artifacts when they are no longer needed.
