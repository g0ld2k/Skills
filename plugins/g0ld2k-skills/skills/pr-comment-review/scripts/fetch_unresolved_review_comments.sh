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

merge_json_array_files() {
  local accumulator_file="$1"
  local page_file="$2"
  local merged_file="$3"

  jq -c -s '.[0] + .[1]' "$accumulator_file" "$page_file" > "$merged_file"
  mv "$merged_file" "$accumulator_file"
}

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

# `gh api graphql --paginate` stops at the FIRST pageInfo object it finds in
# the response, which is the nested comments.pageInfo here rather than the
# outer reviewThreads.pageInfo — that defeats pagination across >100-thread
# PRs. Paginate the outer reviewThreads connection manually instead,
# accumulating thread nodes across pages until hasNextPage is false.
threads_file=""
page_file=""
merge_file=""
thread_input_file=""
enriched_file=""
extra_file=""
cleanup() {
  [[ -z "$threads_file" ]] || rm -f "$threads_file"
  [[ -z "$page_file" ]] || rm -f "$page_file"
  [[ -z "$merge_file" ]] || rm -f "$merge_file"
  [[ -z "$thread_input_file" ]] || rm -f "$thread_input_file"
  [[ -z "$enriched_file" ]] || rm -f "$enriched_file"
  [[ -z "$extra_file" ]] || rm -f "$extra_file"
}
trap cleanup EXIT

threads_file="$(mktemp "${TMPDIR:-/tmp}/fetch-threads.XXXXXX")"
page_file="$(mktemp "${TMPDIR:-/tmp}/fetch-page.XXXXXX")"
merge_file="$(mktemp "${TMPDIR:-/tmp}/fetch-merge.XXXXXX")"
thread_input_file="$(mktemp "${TMPDIR:-/tmp}/fetch-thread-input.XXXXXX")"
enriched_file="$(mktemp "${TMPDIR:-/tmp}/fetch-enriched.XXXXXX")"
extra_file="$(mktemp "${TMPDIR:-/tmp}/fetch-extra.XXXXXX")"
printf '%s' "[]" > "$threads_file"

outer_cursor="null"
outer_has_next="true"

while [[ "$outer_has_next" == "true" ]]; do
  page_result="$(gh api graphql \
    -f query="$query" \
    -F owner="$owner" \
    -F repo="$repo" \
    -F pr="$pr_number" \
    -F endCursor="$outer_cursor")"

  # Merge via files, never argv: a single 100-thread page with large comment
  # bodies can exceed the OS argument-size limit as an --argjson value.
  jq -c '.data.repository.pullRequest.reviewThreads.nodes // []' <<<"$page_result" > "$page_file"
  merge_json_array_files "$threads_file" "$page_file" "$merge_file"
  outer_has_next="$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage // false' <<<"$page_result")"
  outer_cursor="$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // "null"' <<<"$page_result")"
done

# Materialize unresolved threads as NDJSON so jq extraction failures are
# checked by the parent shell. A process substitution would hide that failure
# and could make an incomplete iteration look like a successful empty result.
if ! jq -c '.[] | select(.isResolved == false)' "$threads_file" > "$thread_input_file"; then
  die "could not enumerate unresolved review threads"
fi

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

: > "$enriched_file"
while IFS= read -r thread_json; do
  thread_id="$(jq -r '.id' <<<"$thread_json")"
  has_next="$(jq -r '.comments.pageInfo.hasNextPage' <<<"$thread_json")"
  cursor="$(jq -r '.comments.pageInfo.endCursor' <<<"$thread_json")"

  fetch_failed=false
  # Accumulate reply pages via files for the same argv-limit reason as the
  # outer merge: --argjson values ride on the command line.
  printf '%s' "[]" > "$extra_file"

  while [[ "$has_next" == "true" ]]; do
    if ! follow_up_result="$(gh api graphql \
      -f query="$follow_up_query" \
      -F id="$thread_id" \
      -F endCursor="$cursor" 2>/dev/null)"; then
      fetch_failed=true
      break
    fi

    jq -c '.data.node.comments.nodes // []' <<<"$follow_up_result" > "$page_file"
    merge_json_array_files "$extra_file" "$page_file" "$merge_file"
    has_next="$(jq -r '.data.node.comments.pageInfo.hasNextPage // false' <<<"$follow_up_result")"
    cursor="$(jq -r '.data.node.comments.pageInfo.endCursor // empty' <<<"$follow_up_result")"
  done

  # Merge each thread independently so the accumulated document is never
  # rebuilt once per thread. The thread JSON is piped via stdin rather than
  # passed as a command-line argument, so large comment bodies remain safe.
  jq -c --slurpfile extra "$extra_file" --argjson failed "$fetch_failed" '
    .comments.nodes += $extra[0]
    | .fetch_failed = $failed
  ' <<<"$thread_json" >> "$enriched_file"
done < "$thread_input_file"

# The enriched threads are one JSON object per line. Slurp them from the file
# for the final transform so the complete document never travels through
# argv or shell interpolation.
result_filter='
  def id_from_url: (.url // "" | split("/") | last | tonumber?);
  [.[] as $thread
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
'

if [[ -n "$output_file" ]]; then
  jq -s "$result_filter" "$enriched_file" > "$output_file"
else
  jq -s "$result_filter" "$enriched_file"
fi
