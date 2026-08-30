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

validate_graphql_response() {
  local response="$1"
  local response_kind="${2:-outer}"

  if ! jq -e '
    type == "object"
    and ((has("errors") | not) or (.errors | type == "array" and length == 0))
  ' <<<"$response" >/dev/null; then
    if jq -e 'has("errors") and (.errors | type == "array" and length > 0)' <<<"$response" >/dev/null 2>&1; then
      die "GraphQL errors returned while fetching review threads"
    fi
    die "invalid GraphQL response (errors field is malformed)"
  fi

  local shape_filter='
    def valid_cursor:
      . == null or (type == "string" and length > 0);
    def valid_page_info:
      type == "object"
      and (has("hasNextPage") and has("endCursor"))
      and (.hasNextPage | type == "boolean")
      and (.endCursor | valid_cursor)
      and (.hasNextPage == false or (.endCursor | type == "string" and length > 0));
    def positive_integer:
      type == "number" and . > 0 and floor == .;
    def database_id_from_url:
      if (.url | type == "string" and test("discussion_r[0-9]+$"))
      then (.url | capture("discussion_r(?<id>[0-9]+)$").id | tonumber)
      else null
      end;
    def valid_root_identifier:
      (.databaseId | positive_integer)
      or (database_id_from_url | positive_integer);
    def valid_comment:
      type == "object"
      and (has("databaseId") and has("id") and has("body") and has("path")
        and has("line") and has("originalLine") and has("url")
        and has("createdAt") and has("author") and has("replyTo"))
      and (.id | type == "string" and length > 0)
      and (.databaseId == null or (.databaseId | positive_integer))
      and (.body | type == "string")
      and (.path | type == "string")
      and (.line == null or (.line | type == "number"))
      and (.originalLine == null or (.originalLine | type == "number"))
      and (.url | type == "string" and length > 0)
      and (.createdAt | type == "string" and length > 0)
      and (.author == null or (.author | type == "object" and (.login == null or (.login | type == "string"))))
      and (.replyTo == null or (.replyTo | type == "object" and (.id | type == "string" and length > 0)));
    def valid_comments:
      type == "object"
      and (.nodes | type == "array" and all(.[]; valid_comment))
      and (.pageInfo | valid_page_info);
    def valid_thread:
      type == "object"
      and (has("id") and has("isResolved") and has("comments"))
      and (.id | type == "string" and length > 0)
      and (.isResolved | type == "boolean")
      and (.comments | type == "object")
      and (.comments | valid_comments)
      and ([.comments.nodes[] | select(.replyTo == null)] | length == 1)
      and ([.comments.nodes[] | select(.replyTo == null)][0] | valid_root_identifier);
    '
  if [[ "$response_kind" == "follow_up" ]]; then
    shape_filter+='(
      .data | type == "object"
    )
    and (.data.node | type == "object")
    and (.data.node.comments | valid_comments)
    '
  else
    shape_filter+='(
      .data | type == "object"
    )
    and (.data.repository | type == "object")
    and (.data.repository.pullRequest | type == "object")
    and (.data.repository.pullRequest.reviewThreads | type == "object")
    and (.data.repository.pullRequest.reviewThreads.nodes | type == "array" and all(.[]; valid_thread))
    and (.data.repository.pullRequest.reviewThreads.pageInfo | valid_page_info)
    '
  fi

  if ! jq -e "$shape_filter" <<<"$response" >/dev/null; then
    die "invalid GraphQL response shape while fetching review threads"
  fi
}

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
  if ! page_result="$(gh api graphql \
    -f query="$query" \
    -F owner="$owner" \
    -F repo="$repo" \
    -F pr="$pr_number" \
    -F endCursor="$outer_cursor")"; then
    die "could not fetch review threads"
  fi
  validate_graphql_response "$page_result"

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
# before the jq transform runs. Any failed or malformed follow-up aborts the
# complete fetch rather than returning a partial thread history.
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

  # Accumulate reply pages via files for the same argv-limit reason as the
  # outer merge: --argjson values ride on the command line.
  printf '%s' "[]" > "$extra_file"

  while [[ "$has_next" == "true" ]]; do
    if ! follow_up_result="$(gh api graphql \
      -f query="$follow_up_query" \
      -F id="$thread_id" \
      -F endCursor="$cursor")"; then
      die "could not fetch comments for review thread $thread_id"
    fi
    validate_graphql_response "$follow_up_result" follow_up

    jq -c '.data.node.comments.nodes' <<<"$follow_up_result" > "$page_file"
    merge_json_array_files "$extra_file" "$page_file" "$merge_file"
    has_next="$(jq -r '.data.node.comments.pageInfo.hasNextPage' <<<"$follow_up_result")"
    cursor="$(jq -r '.data.node.comments.pageInfo.endCursor // empty' <<<"$follow_up_result")"
  done

  # Merge each thread independently so the accumulated document is never
  # rebuilt once per thread. The thread JSON is piped via stdin rather than
  # passed as a command-line argument, so large comment bodies remain safe.
  jq -c --slurpfile extra "$extra_file" '
    .comments.nodes += $extra[0]
  ' <<<"$thread_json" >> "$enriched_file"
done < "$thread_input_file"

# The enriched threads are one JSON object per line. Slurp them from the file
# for the final transform so the complete document never travels through
# argv or shell interpolation.
result_filter='
  def id_from_url:
    if (.url | type == "string" and test("discussion_r[0-9]+$"))
    then (.url | capture("discussion_r(?<id>[0-9]+)$").id | tonumber)
    else null
    end;
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
      replies_truncated: false,
      replies: [ $comments[]
        | select(.replyTo != null)
        | { comment_id: .databaseId,
            author: (.author.login // "unknown"),
            body: .body,
            created_at: .createdAt } ]
     }
  ]
  | sort_by(.path, .line, .comment_id)
'

if [[ -n "$output_file" ]]; then
  jq -s "$result_filter" "$enriched_file" > "$output_file"
else
  jq -s "$result_filter" "$enriched_file"
fi
