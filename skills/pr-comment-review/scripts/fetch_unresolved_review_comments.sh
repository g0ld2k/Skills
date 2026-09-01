#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"

usage() { echo "Usage: $0 <owner> <repo> <pr_number> [--output <file>]"; }
if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then usage; exit 0; fi
[[ $# -ge 3 ]] || { usage >&2; exit 1; }

owner="$1"; repo="$2"; pr_number="$3"; shift 3
output_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) output_file="${2:-}"; shift 2 ;;
    *) die "Unknown argument: $1" ;;
  esac
done
[[ "$pr_number" =~ ^[1-9][0-9]*$ ]] || die "PR number must be a positive integer"
require_cmd gh
require_cmd jq

comment_fields='databaseId id body path line originalLine url createdAt author { login } replyTo { id }'
outer_query='query($owner:String!,$repo:String!,$pr:Int!,$cursor:String){
  repository(owner:$owner,name:$repo){pullRequest(number:$pr){
    reviewThreads(first:100,after:$cursor){
      nodes{id isResolved comments(first:100){nodes{ '"$comment_fields"' } pageInfo{hasNextPage endCursor}}}
      pageInfo{hasNextPage endCursor}
    }
  }}
}'
comments_query='query($id:ID!,$cursor:String){
  node(id:$id){... on PullRequestReviewThread{
    comments(first:100,after:$cursor){nodes{ '"$comment_fields"' } pageInfo{hasNextPage endCursor}}
  }}
}'

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/pr-review-fetch.XXXXXX")"
cleanup() { rm -rf "$work_dir"; }
trap cleanup EXIT
threads_file="$work_dir/threads.json"
page_file="$work_dir/page.json"
nodes_file="$work_dir/nodes.json"
merge_file="$work_dir/merge.json"
iterator_file="$work_dir/unresolved.ndjson"
enriched_file="$work_dir/enriched.ndjson"
extra_file="$work_dir/extra.json"
printf '[]' > "$threads_file"

valid_page='def page:
  type == "object"
  and (.nodes | type == "array")
  and (.pageInfo | type == "object")
  and (.pageInfo.hasNextPage | type == "boolean")
  and (.pageInfo.endCursor == null or (.pageInfo.endCursor | type == "string" and length > 0))
  and (.pageInfo.hasNextPage == false or (.pageInfo.endCursor | type == "string" and length > 0));'
valid_comment='def comment:
  type == "object"
  and (.id | type == "string" and length > 0)
  and (.databaseId == null or (.databaseId | type == "number" and . > 0 and floor == .))
  and (.body | type == "string")
  and (.path | type == "string")
  and (.url | type == "string" and length > 0)
  and (.createdAt | type == "string" and length > 0)
  and (.replyTo == null or (.replyTo.id | type == "string" and length > 0));'
valid_root='def root_id:
  (.databaseId | type == "number" and . > 0 and floor == .)
  or (.url | type == "string" and test("discussion_r[0-9]+$"));'
common_shape='type == "object"
  and ((has("errors") | not) or (.errors | type == "array" and length == 0))
  and (.data | type == "object")'

validate_outer() {
  jq -e "$valid_page $valid_comment $valid_root
    $common_shape
    and (.data.repository | type == \"object\")
    and (.data.repository.pullRequest | type == \"object\")
    and (.data.repository.pullRequest.reviewThreads | page)
    and all(.data.repository.pullRequest.reviewThreads.nodes[];
      type == \"object\"
      and (.id | type == \"string\" and length > 0)
      and (.isResolved | type == \"boolean\")
      and (.comments | page)
      and all(.comments.nodes[]; comment)
      and ([.comments.nodes[] | select(.replyTo == null)] | length == 1)
      and ([.comments.nodes[] | select(.replyTo == null)][0] | root_id))" "$1" >/dev/null \
    || die "invalid or unauthorized PR review response"
}

validate_comments() {
  jq -e "$valid_page $valid_comment
    $common_shape
    and (.data.node | type == \"object\")
    and (.data.node.comments | page)
    and all(.data.node.comments.nodes[]; comment)" "$1" >/dev/null \
    || die "invalid review-thread comments response"
}

merge_arrays() {
  jq -c -s '.[0] + .[1]' "$1" "$2" > "$merge_file"
  mv "$merge_file" "$1"
}

cursor="null"; has_next="true"
while [[ "$has_next" == "true" ]]; do
  gh api graphql -f query="$outer_query" -F owner="$owner" -F repo="$repo" \
    -F pr="$pr_number" -F cursor="$cursor" > "$page_file" \
    || die "could not fetch PR review threads"
  validate_outer "$page_file"
  jq -c '.data.repository.pullRequest.reviewThreads.nodes' "$page_file" > "$nodes_file"
  merge_arrays "$threads_file" "$nodes_file"
  has_next="$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage' "$page_file")"
  cursor="$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // "null"' "$page_file")"
done

jq -c '.[] | select(.isResolved == false)' "$threads_file" > "$iterator_file" \
  || die "could not enumerate unresolved review threads"

: > "$enriched_file"
while IFS= read -r thread; do
  thread_id="$(jq -r '.id' <<<"$thread")"
  has_next="$(jq -r '.comments.pageInfo.hasNextPage' <<<"$thread")"
  cursor="$(jq -r '.comments.pageInfo.endCursor // "null"' <<<"$thread")"
  printf '[]' > "$extra_file"
  while [[ "$has_next" == "true" ]]; do
    gh api graphql -f query="$comments_query" -F id="$thread_id" -F cursor="$cursor" > "$page_file" \
      || die "could not complete review thread $thread_id"
    validate_comments "$page_file"
    jq -c '.data.node.comments.nodes' "$page_file" > "$nodes_file"
    merge_arrays "$extra_file" "$nodes_file"
    has_next="$(jq -r '.data.node.comments.pageInfo.hasNextPage' "$page_file")"
    cursor="$(jq -r '.data.node.comments.pageInfo.endCursor // "null"' "$page_file")"
  done
  jq -c --slurpfile extra "$extra_file" '.comments.nodes += $extra[0]' <<<"$thread" >> "$enriched_file" \
    || die "could not assemble review thread $thread_id"
done < "$iterator_file"

result_filter='
  def url_id:
    if (.url | test("discussion_r[0-9]+$"))
    then (.url | capture("discussion_r(?<id>[0-9]+)$").id | tonumber)
    else null end;
  [.[] as $thread
   | $thread.comments.nodes as $comments
   | ($comments[] | select(.replyTo == null)) as $root
   | {
       thread_id: $thread.id,
       is_resolved: false,
       comment_id: ($root.databaseId // ($root | url_id)),
       comment_node_id: $root.id,
       author: ($root.author.login // "unknown"),
       path: $root.path,
       line: ($root.line // $root.originalLine),
       body: $root.body,
       url: $root.url,
       created_at: $root.createdAt,
       replies: [$comments[] | select(.replyTo != null) |
         {comment_id: .databaseId, author: (.author.login // "unknown"), body, created_at: .createdAt}]
     }
   | select(.comment_id != null)]
  | sort_by(.path, .line, .comment_id)'

if [[ -n "$output_file" ]]; then
  jq -s "$result_filter" "$enriched_file" > "$output_file"
else
  jq -s "$result_filter" "$enriched_file"
fi
