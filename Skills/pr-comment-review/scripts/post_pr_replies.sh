#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"

usage() {
  cat <<USAGE
Usage: $0 --owner <owner> --repo <repo> --pr <pr_number> --replies-file <replies.json> [--dry-run]

replies.json format:
[
  { "comment_id": 12345, "thread_id": "PRRT_xxx", "body": "Reply text" }
]

"thread_id" is required: fetch_unresolved_review_comments.sh always emits it,
and it drives a fresh single-thread resolved-and-membership check immediately
before each POST. Entries missing it are skipped rather than falling back to
a batch snapshot that can go stale mid-run.
USAGE
}

owner=""
repo=""
pr_number=""
replies_file=""
dry_run=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)
      owner="${2:-}"
      shift 2
      ;;
    --repo)
      repo="${2:-}"
      shift 2
      ;;
    --pr)
      pr_number="${2:-}"
      shift 2
      ;;
    --replies-file)
      replies_file="${2:-}"
      shift 2
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$owner" || -z "$repo" || -z "$pr_number" || -z "$replies_file" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$replies_file" ]]; then
  die "Replies file not found: $replies_file"
fi

require_cmd gh
require_cmd jq

# Fresh, single-thread check so a reply posted late in a large batch can't
# fire against a thread someone resolved after the batch snapshot was taken.
# Fails closed: a lookup error, missing node, or a comment_id that does not
# actually belong to thread_id all count as "not ok to post" rather than
# silently falling through to "not resolved".
thread_ok_to_post() {
  local thread_id="$1"
  local comment_id="$2"
  local response

  if ! response="$(gh api graphql -f query='
    query($id: ID!) {
      node(id: $id) {
        ... on PullRequestReviewThread {
          isResolved
          comments(first: 100) {
            nodes { databaseId }
          }
        }
      }
    }' -F id="$thread_id")"; then
    return 1
  fi

  local is_resolved
  # Note: avoid `// empty` here — jq's alternative operator treats a real
  # `false` as falsy too, which would misclassify every unresolved thread
  # as a lookup failure. `tostring` keeps `false`/`true`/`null` distinct.
  is_resolved="$(jq -r '.data.node.isResolved | tostring' <<<"$response")"
  if [[ "$is_resolved" != "false" ]]; then
    # Covers isResolved == true and a missing/null node (bad id, API error).
    return 1
  fi

  jq -e --argjson cid "$comment_id" \
    '.data.node.comments.nodes | map(.databaseId) | index($cid) != null' \
    <<<"$response" >/dev/null
}

posted=0
would_post=0
skipped=0
failed=0

while IFS= read -r reply_json; do
  comment_id="$(jq -r '.comment_id // empty' <<<"$reply_json")"
  thread_id="$(jq -r '.thread_id // empty' <<<"$reply_json")"
  body="$(jq -r '.body // ""' <<<"$reply_json")"

  # Malformed input entries count as failed, not skipped: "skipped" is
  # reserved for well-formed entries correctly declined because of live
  # thread state, so a bad replies-file can't look like a clean run.
  if [[ -z "$comment_id" || "$comment_id" == "null" ]]; then
    echo "Failing entry without comment_id" >&2
    failed=$((failed + 1))
    continue
  fi

  if [[ -z "$thread_id" || "$thread_id" == "null" ]]; then
    echo "Failing comment $comment_id (missing required thread_id)" >&2
    failed=$((failed + 1))
    continue
  fi

  # Authoritative, per-reply check: catches a thread resolved after triage,
  # confirms comment_id actually belongs to thread_id, and fails closed on
  # any lookup error.
  if ! thread_ok_to_post "$thread_id" "$comment_id"; then
    echo "Skipping comment $comment_id (thread $thread_id resolved, mismatched, or lookup failed)"
    skipped=$((skipped + 1))
    continue
  fi

  if [[ "$dry_run" == true ]]; then
    echo "DRY RUN: would reply to comment $comment_id"
    would_post=$((would_post + 1))
    continue
  fi

  if gh api -X POST "repos/$owner/$repo/pulls/$pr_number/comments/$comment_id/replies" -f body="$body" >/dev/null; then
    echo "Posted reply to comment $comment_id"
    posted=$((posted + 1))
  else
    echo "Failed posting reply to comment $comment_id" >&2
    failed=$((failed + 1))
  fi
done < <(jq -c '.[]' "$replies_file")

echo "Summary: posted=$posted would_post=$would_post skipped=$skipped failed=$failed dry_run=$dry_run"

if [[ "$failed" -gt 0 ]]; then
  exit 2
fi
