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
replies. A failed, malformed, or stalled page is an error and never a partial
success. Preserve this fetched JSON as the evidence used for triage. Use issue comments only as contextual discussion:

```bash
gh api repos/<owner>/<repo>/issues/<pr_number>/comments --paginate
```

For posting, preview first and execute only with existing posting authorization:

```bash
bash scripts/post_pr_replies.sh --owner <owner> --repo <repo> --pr <pr_number> --replies-file "$out_dir/replies.json" --reviewed-comments-file "$out_dir/unresolved-comments.json" --dry-run
bash scripts/post_pr_replies.sh --owner <owner> --repo <repo> --pr <pr_number> --replies-file "$out_dir/replies.json" --reviewed-comments-file "$out_dir/unresolved-comments.json"
```

Both calls require one JSON array of unique thread/root targets, nonempty bodies,
and the complete fetched conversations actually used for triage. Before each
reply, the helper verifies repository/PR/root identity, resolved state, and the
current root body plus every reply against that reviewed snapshot. Surplus
entries for newly resolved threads are validated and skipped. Changed feedback
requires a fresh fetch and re-triage, using the existing authorization where it
still applies; do not merely replace the snapshot to bypass the check.

A lookup or POST failure stops the remaining batch. Report actual completed
counts and inspect live state before retrying: a network error may follow a
successful write. The helper does not guarantee an atomic batch or exactly-once
writes. Skip equivalent replies already present when preparing a new batch;
use a scoped API operation when only a subset remains. Do not interpret a dry
run as a posted reply. Neither mode resolves threads.

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
  --input <payload.json>
# payload.json is one JSON object: {"body": "Thanks — addressed in <commit-or-explanation>"}
```

## 4) Recommended Posting Policy

- Dry-run preview first.
- Re-check target identity, complete reviewed conversation, and unresolved status before each post.
- Skip any thread now marked resolved.
- Post only within the requested scope and its applicable posting authorization;
  existing authorization does not require another approval turn.
