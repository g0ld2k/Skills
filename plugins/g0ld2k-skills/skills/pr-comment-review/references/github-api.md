# GitHub API Reference (PR Comment Review)

## Purpose

Minimal API surface for fetching unresolved review feedback and posting replies.

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
reply_body_file="$(mktemp "${TMPDIR:-/tmp}/pr-reply-body.XXXXXX")"
reply_payload_file="$(mktemp "${TMPDIR:-/tmp}/pr-reply-payload.XXXXXX")"
printf '%s' 'Thanks — addressed in <commit-or-explanation>' > "$reply_body_file"
jq -n --rawfile body "$reply_body_file" '{body: $body}' > "$reply_payload_file"
gh api -X POST repos/<owner>/<repo>/pulls/<pr_number>/comments/<comment_id>/replies \
  --input "$reply_payload_file"
rm -f "$reply_body_file" "$reply_payload_file"
```

Use `--input` for the JSON payload so a long reply body never becomes a
command-line argument.

## 4) Recommended Posting Policy

- Dry-run preview first.
- Re-check unresolved status before each post.
- Skip any thread now marked resolved.
- Post only after explicit user approval.
