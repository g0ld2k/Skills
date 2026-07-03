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
and it drives a fresh single-thread resolved-and-root-comment check
immediately before each POST. An entry missing comment_id or thread_id is a
hard failure (counted in "failed", exit code 2) — it is not silently
skipped, since a missing required field means the entry can never be
verified or posted correctly.
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
# Also confirms comment_id is the thread's root comment: GitHub's reply
# endpoint only accepts the comment that started the thread, not a reply to
# a reply (https://docs.github.com/en/rest/pulls/comments#create-a-reply-for-a-review-comment).
#
# Return codes distinguish a legitimate skip from a failure so a caller can
# tell "thread already resolved" (fine) apart from "could not verify" or
# "malformed input" (should fail the run, not be swallowed as a skip):
#   0  - ok to post
#   10 - thread is already resolved
#   20 - GraphQL lookup failed, or the node/isResolved shape was unexpected
#   21 - comment_id is not in this thread, or is a reply rather than the
#        thread's root comment
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
            nodes { databaseId replyTo { id } }
          }
        }
      }
    }' -F id="$thread_id")"; then
    return 20
  fi

  local is_resolved
  # Note: avoid `// empty` here — jq's alternative operator treats a real
  # `false` as falsy too, which would misclassify every unresolved thread
  # as a lookup failure. `tostring` keeps `false`/`true`/`null` distinct.
  is_resolved="$(jq -r '.data.node.isResolved | tostring' <<<"$response")"
  if [[ "$is_resolved" == "true" ]]; then
    return 10
  fi
  if [[ "$is_resolved" != "false" ]]; then
    # Missing/null node: bad thread_id or an unexpected API shape.
    return 20
  fi

  if jq -e --argjson cid "$comment_id" '
    (.data.node.comments.nodes | map(select(.databaseId == $cid))) as $m
    | ($m | length) == 1 and ($m[0].replyTo == null)
  ' <<<"$response" >/dev/null; then
    return 0
  fi
  return 21
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
  # confirms comment_id is the thread's root comment, and distinguishes a
  # legitimate skip (already resolved) from a failure (lookup error or
  # malformed comment_id/thread_id pairing) so the latter can't be silently
  # swallowed as "handled".
  rc=0
  thread_ok_to_post "$thread_id" "$comment_id" || rc=$?
  if [[ $rc -eq 10 ]]; then
    echo "Skipping comment $comment_id (thread $thread_id already resolved)"
    skipped=$((skipped + 1))
    continue
  elif [[ $rc -ne 0 ]]; then
    echo "Failing comment $comment_id (thread $thread_id lookup failed or comment_id is not its root comment)" >&2
    failed=$((failed + 1))
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
