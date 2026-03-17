# GitHub API Reference (PR Comment Review)

## Purpose

Minimal API surface for fetching unresolved review feedback and posting replies.

## 1) Fetch Review Threads with Resolved State (GraphQL)

Use GraphQL because REST review comment endpoints do not include thread-level `isResolved`.

```bash
gh api graphql --paginate \
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
            }
          }
          pageInfo{ hasNextPage endCursor }
        }
      }
    }
  }' \
  -F owner=<owner> -F repo=<repo> -F pr=<pr_number>
```

Filter to unresolved threads and top-level review comments (`replyTo == null`).

## 2) Optional Context: PR Issue Comments (REST)

```bash
gh api repos/<owner>/<repo>/issues/<pr_number>/comments --paginate
```

Treat as contextual discussion, not required action items.

## 3) Post Reply to Review Comment (REST)

```bash
gh api -X POST repos/<owner>/<repo>/pulls/comments/<comment_id>/replies \
  -f body='Thanks — addressed in <commit-or-explanation>'
```

## 4) Recommended Posting Policy

- Dry-run preview first.
- Re-check unresolved status before each post.
- Skip any thread now marked resolved.
- Post only after explicit user approval.
