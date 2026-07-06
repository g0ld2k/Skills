#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"

usage() {
  cat <<USAGE
Usage: $0 <owner> <repo> <pr_number> [--output <file>]

Fetch unresolved review threads (root comment plus replies).
Outputs JSON array.
USAGE
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 3 ]]; then
  usage >&2
  exit 1
fi

owner="$1"
repo="$2"
pr_number="$3"
shift 3

output_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      output_file="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

require_cmd gh
require_cmd jq

comment_fields='
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
'

query='query($owner:String!,$repo:String!,$pr:Int!,$endCursor:String){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$pr){
      reviewThreads(first:100, after:$endCursor){
        nodes{
          id
          isResolved
          comments(first:100){
            nodes{
              '"$comment_fields"'
            }
            pageInfo{ hasNextPage endCursor }
          }
        }
        pageInfo{ hasNextPage endCursor }
      }
    }
  }
}'

pages_file="$(mktemp)"
trap 'rm -f "$pages_file"' EXIT

gh api graphql --paginate \
  -f query="$query" \
  -F owner="$owner" \
  -F repo="$repo" \
  -F pr="$pr_number" > "$pages_file"

# Merge every page's reviewThreads.nodes into a single flat array so the
# per-thread pagination loop below (and the final jq transform) can treat the
# whole PR as one list of threads regardless of how many top-level pages
# `--paginate` fetched.
threads_json="$(jq -s '[.[].data.repository.pullRequest.reviewThreads.nodes[]?]' "$pages_file")"

# `gh api graphql --paginate` only follows the top-level reviewThreads cursor;
# it does not paginate each thread's nested comments connection. Any thread
# whose first 100 comments aren't the whole thread needs its own follow-up
# node(id:) queries here, merging fetched comment nodes into that thread
# before the jq transform runs. fetch_failed is set only when a follow-up
# query for that thread errors — never derived from the original page's
# hasNextPage, which stays true even after a successful merge.
follow_up_query='query($id:ID!,$endCursor:String){
  node(id:$id){
    ... on PullRequestReviewThread{
      comments(first:100, after:$endCursor){
        nodes{
          '"$comment_fields"'
        }
        pageInfo{ hasNextPage endCursor }
      }
    }
  }
}'

thread_count="$(jq 'length' <<<"$threads_json")"
for ((i = 0; i < thread_count; i++)); do
  thread_id="$(jq -r ".[$i].id" <<<"$threads_json")"
  has_next="$(jq -r ".[$i].comments.pageInfo.hasNextPage" <<<"$threads_json")"
  cursor="$(jq -r ".[$i].comments.pageInfo.endCursor" <<<"$threads_json")"

  fetch_failed=false
  extra_comments="[]"

  while [[ "$has_next" == "true" ]]; do
    if ! follow_up_result="$(gh api graphql \
      -f query="$follow_up_query" \
      -F id="$thread_id" \
      -F endCursor="$cursor" 2>/dev/null)"; then
      fetch_failed=true
      break
    fi

    page_nodes="$(jq -c '.data.node.comments.nodes // []' <<<"$follow_up_result")"
    extra_comments="$(jq -c --argjson a "$extra_comments" --argjson b "$page_nodes" -n '$a + $b')"
    has_next="$(jq -r '.data.node.comments.pageInfo.hasNextPage // false' <<<"$follow_up_result")"
    cursor="$(jq -r '.data.node.comments.pageInfo.endCursor // empty' <<<"$follow_up_result")"
  done

  threads_json="$(jq --argjson idx "$i" --argjson extra "$extra_comments" --argjson failed "$fetch_failed" '
    .[$idx].comments.nodes += $extra
    | .[$idx].fetch_failed = $failed
  ' <<<"$threads_json")"
done

result="$(jq -n --argjson threads "$threads_json" '
  def id_from_url: (.url // "" | split("/") | last | tonumber?);
  [$threads[] as $thread
   | select($thread.isResolved == false)
   | ($thread.comments.nodes // []) as $comments
   | ($comments[] | select(.replyTo == null)) as $root
   | {
      thread_id: $thread.id,
      is_resolved: $thread.isResolved,
      comment_id: ($root.databaseId // ($root | id_from_url)),
      comment_node_id: $root.id,
      author: ($root.author.login // "unknown"),
      path: ($root.path // ""),
      line: ($root.line // $root.originalLine // null),
      body: $root.body,
      url: $root.url,
      created_at: $root.createdAt,
      replies_truncated: ($thread.fetch_failed // false),
      replies: [ $comments[]
        | select(.replyTo != null)
        | { comment_id: .databaseId,
            author: (.author.login // "unknown"),
            body: .body,
            created_at: .createdAt } ]
     }
   | select(.comment_id != null)
  ]
  | sort_by(.path, .line, .comment_id)
')"

if [[ -n "$output_file" ]]; then
  printf '%s\n' "$result" > "$output_file"
else
  printf '%s\n' "$result"
fi
