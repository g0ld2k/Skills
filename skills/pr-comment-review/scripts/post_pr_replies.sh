#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"
usage() {
  cat <<USAGE
Usage: $0 --owner <owner> --repo <repo> --pr <number> --replies-file <json> --reviewed-comments-file <json> [--dry-run]

Replies: [{"thread_id":"PRRT_xxx","comment_id":123,"body":"Reply text"}]
Reviewed comments: the complete fetch_unresolved_review_comments.sh output used
for triage. Both modes check the current inventory, identity, and conversation.
Resolved threads are skipped. A changed conversation, failed lookup, or uncertain
POST stops the remaining batch. Inspect live state before retrying a failed run.
USAGE
}
owner="" repo="" pr_number="" replies_file="" reviewed_file="" dry_run=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner|--repo|--pr|--replies-file|--reviewed-comments-file)
      [[ $# -ge 2 && -n $2 ]] || die "Missing value for $1"
      case "$1" in
        --owner) owner="$2" ;; --repo) repo="$2" ;; --pr) pr_number="$2" ;;
        --replies-file) replies_file="$2" ;; --reviewed-comments-file) reviewed_file="$2" ;;
      esac
      shift 2 ;;
    --dry-run) dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done
[[ -n "$owner" && -n "$repo" && "$pr_number" =~ ^[1-9][0-9]*$ && -f "$replies_file" && -f "$reviewed_file" ]] || { usage >&2; exit 1; }
require_cmd gh
require_cmd jq
scratch="$(mktemp -d "${TMPDIR:-/tmp}/post-review.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT
cp "$replies_file" "$scratch/replies.json"
cp "$reviewed_file" "$scratch/reviewed.json"
# Parse exactly one document and snapshot it before any network writes. Reject
# duplicate roots as well as duplicate threads, including concatenated arrays.
if ! jq -es '
  def id: type == "number" and . > 0 and . == floor;
  length == 1 and (.[0] | type == "array"
    and all(.[]; (.thread_id | type == "string" and length > 0)
      and (.comment_id | id) and (.body | type == "string" and test("\\S")))
    and (map(.thread_id) | length == (unique | length))
    and (map(.comment_id) | length == (unique | length)))
' "$scratch/replies.json" >/dev/null; then die "Invalid replies: expected one array with unique targets, positive integer IDs, and nonempty bodies"; fi
if ! jq -es 'length == 1 and (.[0] | type == "array"
  and all(.[]; (.thread_id | type == "string") and (.comment_id | type == "number")
    and (.body | type == "string") and .replies_truncated == false
    and (.replies | type == "array" and all(.[]; (.comment_id | type == "number")
      and (.body | type == "string") and (.author | type == "string"))))
  and (map(.thread_id) | length == (unique | length)))' "$scratch/reviewed.json" >/dev/null; then
  die "Invalid or incomplete reviewed-comments snapshot"
fi
jq -e --slurpfile reviewed "$scratch/reviewed.json" '
  [.[] | {thread_id, comment_id}] - [$reviewed[0][] | {thread_id, comment_id}] | length == 0
' "$scratch/replies.json" >/dev/null || die "Replies lack a reviewed conversation"
bash "$script_dir/fetch_unresolved_review_comments.sh" "$owner" "$repo" "$pr_number" --output "$scratch/current.json"
jq -e --slurpfile current "$scratch/current.json" '
  [$current[0][] | {thread_id, comment_id}] - [.[] | {thread_id, comment_id}] | length == 0
' "$scratch/replies.json" >/dev/null || die "Reply inventory does not match current unresolved comments"
jq -c '.[]' "$scratch/replies.json" > "$scratch/replies.jsonl"

# This check is target-specific, not a promise of an atomic multi-thread write.
# Return 10 only for a verified, correctly paired, already-resolved thread.
thread_ok_to_post() {
  local thread_id="$1" comment_id="$2"
  gh api graphql -f query='query($id:ID!){node(id:$id){... on PullRequestReviewThread{isResolved pullRequest{number repository{owner{login} name}} comments(first:100){nodes{'"$review_comment_fields"'} pageInfo{hasNextPage endCursor}}}}}' -F id="$thread_id" > "$scratch/live.json" || return 20
  jq -se --arg owner "$owner" --arg repo "$repo" --argjson pr "$pr_number" '
    length == 1 and (.[0] |
    (.errors == null or (.errors | type == "array" and length == 0))
    and (.data.node.isResolved | type == "boolean")
    and ((.data.node.pullRequest.repository.owner.login | ascii_downcase) == ($owner | ascii_downcase))
    and ((.data.node.pullRequest.repository.name | ascii_downcase) == ($repo | ascii_downcase))
    and .data.node.pullRequest.number == $pr)
  ' "$scratch/live.json" >/dev/null || return 20
  complete_connection "$scratch/live.json" '.data.node.comments' "$review_comments_query" "$scratch/comments.json" -F id="$thread_id" || return 20
  format_review_thread "$thread_id" "$scratch/comments.json" > "$scratch/thread.json" || return 20
  jq -e --argjson cid "$comment_id" '.comment_id == $cid' "$scratch/thread.json" >/dev/null || return 20
  if [[ "$(jq -r '.data.node.isResolved' "$scratch/live.json")" == true ]]; then return 10; fi
  jq -e --arg tid "$thread_id" --slurpfile live "$scratch/thread.json" '
    def conversation: {body, replies: [.replies[] | {comment_id, author, body}]};
    map(select(.thread_id == $tid)) as $reviewed
    | ($reviewed | length) == 1 and (($reviewed[0] | conversation) == ($live[0] | conversation))
  ' "$scratch/reviewed.json" >/dev/null || return 20
}
posted=0 would_post=0 skipped=0 failed=0
while IFS= read -r item; do
  comment_id="$(jq -r '.comment_id' <<<"$item")"
  thread_id="$(jq -r '.thread_id' <<<"$item")"
  rc=0
  thread_ok_to_post "$thread_id" "$comment_id" || rc=$?
  if [[ $rc -eq 10 ]]; then
    echo "Skipping comment $comment_id (thread $thread_id already resolved)"
    skipped=$((skipped + 1)); continue
  elif [[ $rc -ne 0 ]]; then
    echo "Stopped at comment $comment_id: could not verify target or reviewed conversation. Refresh and re-triage before continuing." >&2
    failed=$((failed + 1)); break
  fi
  if [[ "$dry_run" == true ]]; then
    echo "DRY RUN: would reply to comment $comment_id"
    would_post=$((would_post + 1)); continue
  fi
  # Preserve arbitrarily large bodies and trailing newlines through a JSON file.
  jq '{body}' <<<"$item" > "$scratch/payload.json"
  if gh api -X POST "repos/$owner/$repo/pulls/$pr_number/comments/$comment_id/replies" --input "$scratch/payload.json" > /dev/null; then
    echo "Posted reply to comment $comment_id"
    posted=$((posted + 1))
  else
    echo "Unconfirmed POST for comment $comment_id. Inspect live state before retrying; remaining replies were not attempted." >&2
    failed=$((failed + 1)); break
  fi
done < "$scratch/replies.jsonl"
echo "Summary: posted=$posted would_post=$would_post skipped=$skipped failed=$failed dry_run=$dry_run"
[[ "$failed" -eq 0 ]] || exit 2
