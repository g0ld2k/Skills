# GitHub API Reference (PR Comment Review)

## Purpose

Minimal API surface for fetching unresolved review feedback and posting replies.

## MCP Operations

Load this section when using MCP. Resolve owner/repo/PR and fetch thread-level
resolved state with all comment pages. Emit the same thread/root-comment fields
as the CLI helper. For posting, preview replies and apply SKILL.md's complete
inventory, nonempty body, repository/PR/root-comment identity, and fresh
unresolved-state checks. A lookup failure is a blocker, not a resolved skip.
If a capability cannot supply these checks, use the CLI or block that operation.
The authorization gate in SKILL.md applies equally to MCP and CLI.

## CLI Helpers

Load this section when using the CLI. Resolve script paths relative to this
skill directory, not the target repository. Helpers require `gh` and `jq`;
use authenticated MCP if the CLI cannot perform the operation.

```bash
out_dir="$(mktemp -d "${TMPDIR:-/tmp}/pr-review.XXXXXX")"
bash scripts/fetch_unresolved_review_comments.sh <owner> <repo> <pr_number> --output "$out_dir/unresolved-comments.json"
bash scripts/build_triage_template.sh --input "$out_dir/unresolved-comments.json"
```

The fetch helper returns only unresolved threads, including root comments and
replies. Use issue comments only as contextual discussion:

```bash
gh api repos/<owner>/<repo>/issues/<pr_number>/comments --paginate
```

For posting, preview first and execute only with existing posting authorization:

```bash
bash scripts/post_pr_replies.sh --owner <owner> --repo <repo> --pr <pr_number> --replies-file "$out_dir/replies.json" --dry-run
bash scripts/post_pr_replies.sh --owner <owner> --repo <repo> --pr <pr_number> --replies-file "$out_dir/replies.json"
```

Both calls verify complete current reply inventory, nonempty bodies, target
identity, and fresh resolved state. Surplus entries for newly resolved threads
are validated and skipped. Distinguish skips from lookup/input failures and
report the helper's actual counts. Do not interpret a dry run as a posted reply.

## Raw API Operations

Load the following sections only to implement an equivalent fetch/post operation
or diagnose helper behavior. Prefer the helpers when they meet the task.

## 1) Fetch Review Threads with Resolved State (GraphQL)

Use GraphQL because REST review comment endpoints do not include thread-level `isResolved`.

Do NOT use `gh api graphql --paginate` with this query: `--paginate` follows
the FIRST `pageInfo` it finds, which is the nested `comments.pageInfo` here,
so outer thread pagination silently breaks past 100 threads. Loop manually:
pass `-F endCursor=<cursor>` from `reviewThreads.pageInfo.endCursor` until
`hasNextPage` is false, and complete any thread whose `comments.pageInfo`
reports more pages with follow-up `node(id:)` queries.

```bash
gh api graphql \
  -f query='query($owner:String!,$repo:String!,$pr:Int!,$endCursor:String){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$pr){
        reviewThreads(first:100, after:$endCursor){
          nodes{
            id
            isResolved
            comments(first:100){
              nodes{
                databaseId
                id
                body
                path
                line
                originalLine
                url
                createdAt
                author{ login }
                replyTo{ id }
              }
              pageInfo{ hasNextPage endCursor }
            }
          }
          pageInfo{ hasNextPage endCursor }
        }
      }
    }
  }' \
  -F owner=<owner> -F repo=<repo> -F pr=<pr_number>
```

Filter to unresolved threads; emit each thread's root comment plus its
replies, paginating a thread's comments (follow-up `node(id:)` queries) when
`hasNextPage` is true.

## 2) Optional Context: PR Issue Comments (REST)

```bash
gh api repos/<owner>/<repo>/issues/<pr_number>/comments --paginate
```

Treat as contextual discussion, not required action items.

## 3) Post Reply to Review Comment (REST)

```bash
gh api -X POST repos/<owner>/<repo>/pulls/<pr_number>/comments/<comment_id>/replies \
  -f body='Thanks — addressed in <commit-or-explanation>'
```

## 4) Recommended Posting Policy

- Dry-run preview first.
- Re-check unresolved status before each post.
- Skip any thread now marked resolved.
- Post only with explicit user authorization from the conversation or caller;
  existing authorization does not require another approval turn.
