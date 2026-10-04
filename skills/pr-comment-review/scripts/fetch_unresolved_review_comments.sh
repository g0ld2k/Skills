#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"

usage() {
  echo "Usage: $0 <owner> <repo> <pr_number> [--output <file>]"
  echo "Fetch complete unresolved review conversations as a JSON array."
}
if [[ ${1:-} == -h || ${1:-} == --help ]]; then usage; exit 0; fi
[[ $# -ge 3 ]] || { usage >&2; exit 1; }
owner="$1" repo="$2" pr_number="$3"
shift 3
output_file=""
if [[ $# -gt 0 ]]; then
  [[ $# -eq 2 && $1 == --output && -n $2 ]] || { usage >&2; exit 1; }
  output_file="$2"
fi
[[ "$pr_number" =~ ^[1-9][0-9]*$ ]] || die "PR number must be a positive integer"
require_cmd gh
require_cmd jq
scratch="$(mktemp -d "${TMPDIR:-/tmp}/fetch-review.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT
query='query($owner:String!,$repo:String!,$pr:Int!,$endCursor:String){repository(owner:$owner,name:$repo){pullRequest(number:$pr){reviewThreads(first:100,after:$endCursor){nodes{id isResolved comments(first:100){nodes{'"$(review_comment_fields)"'} pageInfo{hasNextPage endCursor}}} pageInfo{hasNextPage endCursor}}}}}'
gh api graphql -f query="$query" -F owner="$owner" -F repo="$repo" -F pr="$pr_number" -F endCursor=null > "$scratch/first.json"
complete_connection "$scratch/first.json" '.data.repository.pullRequest.reviewThreads' "$query" "$scratch/threads.json" -F owner="$owner" -F repo="$repo" -F pr="$pr_number"
jq -e 'all(.[]; (.id | type == "string" and length > 0) and (.isResolved | type == "boolean"))
  and (map(.id) | length == (unique | length))' "$scratch/threads.json" >/dev/null || die "Invalid or duplicate review threads"
jq -c '.[] | select(.isResolved == false)' "$scratch/threads.json" > "$scratch/unresolved.jsonl"
: > "$scratch/results.jsonl"
while IFS= read -r item; do
  thread_id="$(jq -r '.id' <<<"$item")"
  # Wrap the initial nested connection to share the follow-up node query shape.
  jq '{data:{node:{comments:.comments}}}' <<<"$item" > "$scratch/thread.json"
  complete_connection "$scratch/thread.json" '.data.node.comments' "$(review_comments_query)" "$scratch/comments.json" -F id="$thread_id"
  format_review_thread "$thread_id" "$scratch/comments.json" >> "$scratch/results.jsonl"
done < "$scratch/unresolved.jsonl"
jq -s 'sort_by(.path, .line, .comment_id)' "$scratch/results.jsonl" > "$scratch/result.json"
# Leave an existing output untouched if any fetch/validation failed.
if [[ -n "$output_file" ]]; then cp "$scratch/result.json" "$output_file"; else cat "$scratch/result.json"; fi
