#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"

usage() {
  cat <<USAGE
Usage: $0 <owner> <repo> <pr_number> [--output <file>]

Fetch top-level review comments from unresolved review threads only.
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

query='query($owner:String!,$repo:String!,$pr:Int!,$endCursor:String){
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
}'

result="$({
  gh api graphql --paginate \
    -f query="$query" \
    -F owner="$owner" \
    -F repo="$repo" \
    -F pr="$pr_number"
} | jq -s '
  def id_from_url: (.url // "" | split("/") | last | tonumber?);
  [.[].data.repository.pullRequest.reviewThreads.nodes[]? as $thread
   | select($thread.isResolved == false)
   | $thread.comments.nodes[]?
   | select(.replyTo == null)
   | {
      thread_id: $thread.id,
      is_resolved: $thread.isResolved,
      comment_id: (.databaseId // id_from_url),
      comment_node_id: .id,
      author: (.author.login // "unknown"),
      path: (.path // ""),
      line: (.line // .originalLine // null),
      body: .body,
      url: .url,
      created_at: .createdAt
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
