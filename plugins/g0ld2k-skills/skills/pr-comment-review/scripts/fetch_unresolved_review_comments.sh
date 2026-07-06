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
threads_file="$(mktemp)"
next_file="$(mktemp)"
extra_file="$(mktemp)"
page_nodes_file="$(mktemp)"
trap 'rm -f "$pages_file" "$threads_file" "$next_file" "$extra_file" "$page_nodes_file"' EXIT

has_next=true
end_cursor=""
while [[ "$has_next" == "true" ]]; do
  query_args=(-f query="$query" -F owner="$owner" -F repo="$repo" -F pr="$pr_number")
  if [[ -n "$end_cursor" ]]; then
    query_args+=(-F endCursor="$end_cursor")
  fi

  page_result="$(gh api graphql "${query_args[@]}")"
  printf '%s\n' "$page_result" >> "$pages_file"
  has_next="$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage // false' <<<"$page_result")"
  end_cursor="$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // empty' <<<"$page_result")"
done

# Merge every page's reviewThreads.nodes into a single flat array so the
# per-thread pagination loop below (and the final jq transform) can treat the
# whole PR as one list of threads regardless of how many top-level pages
# were fetched.
jq -s '[.[].data.repository.pullRequest.reviewThreads.nodes[]?]' "$pages_file" > "$threads_file"

# The top-level reviewThreads query does not paginate each thread's nested
# comments connection. Any thread whose first 100 comments aren't the whole
# thread needs its own follow-up node(id:) queries here, merging fetched
# comment nodes into that thread before the jq transform runs. fetch_failed is
# set only when a follow-up query for that thread errors — never derived from
# the original page's hasNextPage, which stays true even after a successful
# merge.
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

thread_count="$(jq 'length' "$threads_file")"
for ((i = 0; i < thread_count; i++)); do
  thread_id="$(jq -r ".[$i].id" "$threads_file")"
  has_next="$(jq -r ".[$i].comments.pageInfo.hasNextPage" "$threads_file")"
  cursor="$(jq -r ".[$i].comments.pageInfo.endCursor" "$threads_file")"

  fetch_failed=false
  printf '[]\n' > "$extra_file"

  while [[ "$has_next" == "true" ]]; do
    if ! follow_up_result="$(gh api graphql \
      -f query="$follow_up_query" \
      -F id="$thread_id" \
      -F endCursor="$cursor" 2>/dev/null)"; then
      fetch_failed=true
      break
    fi

    jq '.data.node.comments.nodes // []' <<<"$follow_up_result" > "$page_nodes_file"
    jq -s '.[0] + .[1]' "$extra_file" "$page_nodes_file" > "$next_file"
    mv "$next_file" "$extra_file"
    has_next="$(jq -r '.data.node.comments.pageInfo.hasNextPage // false' <<<"$follow_up_result")"
    cursor="$(jq -r '.data.node.comments.pageInfo.endCursor // empty' <<<"$follow_up_result")"
  done

  jq --argjson idx "$i" --slurpfile extra "$extra_file" --argjson failed "$fetch_failed" '
    .[$idx].comments.nodes += $extra[0]
    | .[$idx].fetch_failed = $failed
  ' "$threads_file" > "$next_file"
  mv "$next_file" "$threads_file"
done

result="$(jq '
  def id_from_url: (.url // "" | split("/") | last | tonumber?);
  [.[] as $thread
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
' "$threads_file")"

if [[ -n "$output_file" ]]; then
  printf '%s\n' "$result" > "$output_file"
else
  printf '%s\n' "$result"
fi
