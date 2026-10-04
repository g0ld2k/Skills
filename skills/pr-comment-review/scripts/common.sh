#!/usr/bin/env bash

die() {
  echo "$*" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "$cmd is required"
}

# Complete one GraphQL connection. Initial and subsequent pages use the same
# selector. Never publish partial data or trust an error response as an empty list.
complete_connection() (
  local first="$1" selector="$2" query="$3" output="$4"
  shift 4
  local scratch cursor prior has_next
  local seen=()
  scratch="$(mktemp -d "${TMPDIR:-/tmp}/review-pages.XXXXXX")" || exit 1
  trap 'rm -rf "$scratch"' EXIT
  cp "$first" "$scratch/page.json" || exit 1
  printf '[]\n' > "$scratch/all.json"
  while true; do
    if ! jq -se "
      length == 1 and (.[0] |
      (.errors == null or (.errors | type == \"array\" and length == 0))
      and ($selector | type == \"object\"
        and (.nodes | type == \"array\" and all(.[]; type == \"object\"))
        and (.pageInfo.hasNextPage | type == \"boolean\")))
    " "$scratch/page.json" >/dev/null; then
      echo "Incomplete or invalid GraphQL connection ($selector)" >&2
      exit 1
    fi
    jq "$selector.nodes" "$scratch/page.json" > "$scratch/nodes.json" || exit 1
    jq -s '.[0] + .[1]' "$scratch/all.json" "$scratch/nodes.json" > "$scratch/merged.json" || exit 1
    mv "$scratch/merged.json" "$scratch/all.json" || exit 1
    has_next="$(jq -r "$selector.pageInfo.hasNextPage" "$scratch/page.json")"
    [[ "$has_next" == true ]] || break
    cursor="$(jq -er "$selector.pageInfo.endCursor | select(type == \"string\" and length > 0)" "$scratch/page.json")" || {
      echo "Missing pagination cursor" >&2; exit 1;
    }
    for prior in "${seen[@]+"${seen[@]}"}"; do
      if [[ "$prior" == "$cursor" ]]; then
        echo "Repeated pagination cursor" >&2
        exit 1
      fi
    done
    seen+=("$cursor")
    gh api graphql -f query="$query" "$@" -F endCursor="$cursor" > "$scratch/page.json" || exit 1
  done
  cp "$scratch/all.json" "$output"
)

review_comment_fields() {
  printf '%s\n' 'databaseId id body path line originalLine url createdAt author { login } replyTo { id }'
}
review_comments_query() {
  printf '%s\n' 'query($id:ID!,$endCursor:String){node(id:$id){... on PullRequestReviewThread{comments(first:100,after:$endCursor){nodes{'"$(review_comment_fields)"'} pageInfo{hasNextPage endCursor}}}}}'
}

# Normalize a complete conversation. Missing roots or IDs are errors, not threads
# to silently omit. The URL fallback is GitHub's actual discussion fragment.
format_review_thread() {
  jq --arg thread "$1" '
    def numeric_id:
      (.databaseId // (.url // "" | try capture("#discussion_r(?<id>[0-9]+)$").id | tonumber))
      | select(type == "number" and . > 0 and . == floor);
    if (length > 0 and all(.[]; (.body | type == "string") and (.id | type == "string")
          and (has("replyTo") and (.replyTo == null or (.replyTo.id | type == "string"))))
        and (map(.id) | length == (unique | length))) | not
    then error("Incomplete or duplicate comment data") else . end
    | . as $comments
    | map(select(.replyTo == null)) as $roots
    | if ($roots | length) != 1 then error("Expected one root comment") else $roots[0] end
    | . as $root
    | ([$root | numeric_id]) as $ids
    | if ($ids | length) != 1 then error("Missing root comment ID") else . end
    | {thread_id: $thread, is_resolved: false, comment_id: $ids[0],
       comment_node_id: $root.id, author: ($root.author.login // "unknown"),
       path: ($root.path // ""), line: ($root.line // $root.originalLine // null),
       body: $root.body, url: $root.url, created_at: $root.createdAt,
       replies_truncated: false,
       replies: [$comments[] | select(.replyTo != null)
         | ([numeric_id]) as $ids
         | if ($ids | length) != 1 then error("Missing reply ID") else . end
         | {comment_id: $ids[0], author: (.author.login // "unknown"), body,
            created_at: .createdAt}]}
  ' "$2"
}
