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
and it drives a fresh check immediately before each POST that the thread
belongs to the given --owner/--repo/--pr, is unresolved, and that
comment_id is its root comment. An entry missing comment_id or thread_id,
or one that fails any of those checks for a reason other than "already
resolved", is a hard failure (counted in "failed", exit code 2) — it is
not silently skipped.
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
#   22 - thread belongs to a different repo/PR than --owner/--repo/--pr
thread_ok_to_post() {
  local thread_id="$1"
  local comment_id="$2"
  local response

  if ! response="$(gh api graphql -f query='
    query($id: ID!) {
      node(id: $id) {
        ... on PullRequestReviewThread {
          isResolved
          pullRequest {
            number
            repository {
              owner { login }
              name
            }
          }
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
  if [[ "$is_resolved" != "true" && "$is_resolved" != "false" ]]; then
    # Missing/null node: bad thread_id or an unexpected API shape.
    return 20
  fi

  # Confirm the thread actually belongs to the requested --owner/--repo/--pr.
  # thread_id is a global node ID with no inherent tie to the CLI args, so a
  # replies file built for a different PR (or reused against the wrong one)
  # would otherwise only surface as a late POST failure — or not at all in
  # --dry-run, since dry-run never reaches the POST call.
  # Downcase both sides in jq rather than bash: `${var,,}` needs bash 4+,
  # but macOS ships bash 3.2 by default under `/usr/bin/env bash`.
  if ! jq -e --arg owner "$owner" --arg repo "$repo" --argjson pr "$pr_number" '
    (.data.node.pullRequest.repository.owner.login | ascii_downcase) == ($owner | ascii_downcase)
    and (.data.node.pullRequest.repository.name | ascii_downcase) == ($repo | ascii_downcase)
    and .data.node.pullRequest.number == $pr
  ' <<<"$response" >/dev/null; then
    return 22
  fi

  # Check root-comment membership before treating isResolved as a benign
  # skip: a mismatched pairing (comment_id doesn't actually belong to
  # thread_id) must fail even when thread_id happens to be resolved,
  # otherwise the real, unresolved target comment silently never gets a
  # reply while the batch reports a clean skip.
  if ! jq -e --argjson cid "$comment_id" '
    (.data.node.comments.nodes | map(select(.databaseId == $cid))) as $m
    | ($m | length) == 1 and ($m[0].replyTo == null)
  ' <<<"$response" >/dev/null; then
    return 21
  fi

  if [[ "$is_resolved" == "true" ]]; then
    return 10
  fi
  return 0
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
    echo "Failing comment $comment_id (thread $thread_id: lookup failed, wrong repo/PR, or comment_id is not its root comment)" >&2
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
