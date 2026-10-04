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

Resolve these identities before lookup: `BASE_REPO` is the target repository
(`owner/repo`), `BASE_BRANCH` its requested base, and `HEAD_REPO`, `HEAD_OWNER`,
and `BRANCH` identify the source repository, owner, and branch. For creation,
set `HEAD_REF` to `$BRANCH` for a same-repository PR or `$HEAD_OWNER:$BRANCH`
for a fork. If the CLI cannot represent that head repository, use an equivalent
API without changing the target.

Find open PRs in that base repository using the qualified head; read every page:

```bash
gh api --method GET "repos/$BASE_REPO/pulls" --paginate \
  -f state=open -f head="$HEAD_OWNER:$BRANCH"
```

Match each candidate's `head.repo.full_name` and `head.ref` to `HEAD_REPO` and
`BRANCH`, and check `base.ref` against `BASE_BRANCH`. Use `PR_NUMBER` from the
unique matching open PR. A failed, incomplete, or ambiguous lookup blocks
publication. An existing PR for that head with only a different base is a base
mismatch, not permission to retarget or create another PR. Only a successful,
complete lookup with no PR for the verified head establishes absence.

For an existing PR, inspect that same repository and confirm its identities:

```bash
gh pr view "$PR_NUMBER" --repo "$BASE_REPO" \
  --json number,url,title,state,baseRefName,headRefName,headRepository,headRepositoryOwner
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
gh pr edit "$PR_NUMBER" --repo "$BASE_REPO" \
  --title "<title>" --body-file "$pr_body_file"
```

For a new PR, resolve the destination repository and head ref explicitly; do not
assume a remote named origin is the intended destination. Push only with covered
authority, using an ordinary fast-forward push for create and update alike.
If the remote ref already exists, inspect its relationship before pushing;
a PR-create request never authorizes replacing another branch's history. Do not
escalate a rejection to force-with-lease without separate rewrite authority.

With the example's origin verified as the push destination in `HEAD_REPO`, create
using the same resolved identities (add `--draft` when a draft was requested):

```bash
git push -u origin "$BRANCH"
gh pr create --repo "$BASE_REPO" --title "<title>" --body-file "$pr_body_file" \
  --base "$BASE_BRANCH" --head "$HEAD_REF"
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
