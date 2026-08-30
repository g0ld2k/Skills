#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"

usage() {
  cat <<USAGE
Usage: $0 --owner <owner> --repo <repo> --pr <pr_number> --replies-file <replies.json> [--dry-run] [--preview-file <preview.json>] [--approved-digest <sha256:...>]

replies.json format:
[
  { "comment_id": 12345, "thread_id": "PRRT_xxx", "body": "Reply text" }
]

"thread_id" is required: fetch_unresolved_review_comments.sh always emits it,
and it drives a fresh check immediately before each POST that the thread
belongs to the given --owner/--repo/--pr, is unresolved, and that
comment_id is its root comment. "body" must be a nonempty string. An entry
missing any required field, or one that fails any of those checks for a reason
other than "already resolved", is a hard failure (counted in "failed", exit
code 2) — it is not silently skipped.

Dry-run writes an exact canonical approval artifact when --preview-file is
provided, and prints its SHA-256 digest. A non-dry-run requires that same
--preview-file and its approved digest; it verifies the owner/repo/PR, thread
IDs, root comment IDs, and reply bodies before any POST.
USAGE
}

owner=""
repo=""
pr_number=""
replies_file=""
dry_run=false
preview_file=""
approved_digest=""

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
    --preview-file)
      preview_file="${2:-}"
      shift 2
      ;;
    --approved-digest)
      approved_digest="${2:-}"
      shift 2
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

if ! [[ "$pr_number" =~ ^[1-9][0-9]*$ ]]; then
  die "PR number must be a positive integer"
fi

if [[ "$dry_run" == false ]]; then
  if [[ -z "$preview_file" || -z "$approved_digest" ]]; then
    die "--preview-file and --approved-digest are required for non-dry-run posting; run a dry-run first"
  fi
  if [[ ! -f "$preview_file" ]]; then
    die "Preview file not found: $preview_file"
  fi
  if ! [[ "$approved_digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    die "--approved-digest must be sha256 followed by 64 lowercase hexadecimal characters"
  fi
fi

if [[ ! -f "$replies_file" ]]; then
  die "Replies file not found: $replies_file"
fi

require_cmd gh
require_cmd jq
require_cmd awk

sha256_file() {
  local path="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
  else
    die "shasum or sha256sum is required for approval previews"
  fi
}

# Refuse partial or duplicated reply batches before checking or posting any
# individual thread. A clean dry-run must prove that the replies file accounts
# for every currently unresolved top-level review comment exactly once. Surplus
# entries are allowed through so the per-thread check can safely skip comments
# whose threads were resolved after the replies file was prepared.
fetch_script="$script_dir/fetch_unresolved_review_comments.sh"
unresolved_file=""
reply_iterator_file=""
reply_payload_file=""
canonical_preview_file=""
cleanup() {
  [[ -z "$unresolved_file" ]] || rm -f "$unresolved_file"
  [[ -z "$reply_iterator_file" ]] || rm -f "$reply_iterator_file"
  [[ -z "$reply_payload_file" ]] || rm -f "$reply_payload_file"
  [[ -z "$canonical_preview_file" ]] || rm -f "$canonical_preview_file"
}
trap cleanup EXIT

unresolved_file="$(mktemp "${TMPDIR:-/tmp}/post-replies-unresolved.XXXXXX")"
reply_iterator_file="$(mktemp "${TMPDIR:-/tmp}/post-replies-iterator.XXXXXX")"
reply_payload_file="$(mktemp "${TMPDIR:-/tmp}/post-reply-payload.XXXXXX")"
canonical_preview_file="$(mktemp "${TMPDIR:-/tmp}/post-replies-preview.XXXXXX")"

# Read replies.json exactly once. Every later gate and POST derives from this
# canonical snapshot, so changing the source file mid-run cannot change the
# approved batch.
if ! jq -ce --arg owner "$owner" --arg repo "$repo" --argjson pr "$pr_number" '
  def positive_integer:
    type == "number" and . > 0 and floor == .;
  if type == "array"
    and all(.[];
      type == "object"
      and (.thread_id | type == "string" and length > 0)
      and (.comment_id | positive_integer)
      and (.body | type == "string" and length > 0))
  then {
    owner: $owner,
    repo: $repo,
    pr: $pr,
    replies: [.[] | {thread_id, comment_id, body}]
  }
  else error("invalid replies file")
  end
' "$replies_file" > "$canonical_preview_file"; then
  echo "Failing replies file (each entry requires thread_id, positive-integer comment_id, and nonempty string body)" >&2
  exit 2
fi

if [[ "$dry_run" == false ]]; then
  preview_digest="$(sha256_file "$canonical_preview_file")"
  if [[ "sha256:$preview_digest" != "$approved_digest" ]]; then
    echo "Failing approval preview (approved digest does not match preview artifact)" >&2
    exit 2
  fi
  if ! cmp -s "$canonical_preview_file" "$preview_file"; then
    echo "Failing approval preview (preview does not match current target or reply bodies)" >&2
    exit 2
  fi
  echo "Using approved preview: $preview_file"
  echo "Preview digest: $approved_digest"
fi

if ! bash "$fetch_script" "$owner" "$repo" "$pr_number" --output "$unresolved_file"; then
  echo "Failing replies file (could not fetch current unresolved review threads)" >&2
  exit 2
fi

if ! jq -e --slurpfile unresolved "$unresolved_file" '
  [.replies[] | {thread_id, comment_id}] as $reply_pairs
  | [$unresolved[0][] | {thread_id, comment_id}] as $required_pairs
  | ($reply_pairs | length) == ($reply_pairs | unique_by(.thread_id) | length)
    and (($required_pairs - $reply_pairs) | length == 0)
' "$canonical_preview_file" >/dev/null; then
  echo "Failing replies file (reply inventory does not match current unresolved top-level review comments)" >&2
  exit 2
fi

# Materialize the replies iterator so jq extraction failures are checked by
# the parent shell. A process substitution would hide that failure and could
# make an incomplete batch look like a successful empty run.
if ! jq -c '.replies[]' "$canonical_preview_file" > "$reply_iterator_file"; then
  echo "Failing replies file (could not enumerate reply entries)" >&2
  exit 2
fi

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

  # GraphQL may return partial data alongside errors. Treat both the error
  # state and every field consumed below as untrusted so partial or malformed
  # data can never authorize a POST.
  if ! jq -e '
    type == "object"
    and ((has("errors") | not) or (.errors | type == "array" and length == 0))
    and (.data | type == "object")
    and (.data.node | type == "object")
    and (.data.node.isResolved | type == "boolean")
    and (.data.node.pullRequest | type == "object")
    and (.data.node.pullRequest.number | type == "number")
    and (.data.node.pullRequest.repository | type == "object")
    and (.data.node.pullRequest.repository.owner | type == "object")
    and (.data.node.pullRequest.repository.owner.login | type == "string" and length > 0)
    and (.data.node.pullRequest.repository.name | type == "string" and length > 0)
    and (.data.node.comments | type == "object")
    and (.data.node.comments.nodes | type == "array")
    and all(.data.node.comments.nodes[];
      type == "object"
      and has("databaseId")
      and has("replyTo")
      and (.databaseId | type == "number" and . > 0 and floor == .)
      and (.replyTo == null or
        (.replyTo | type == "object"
          and (.id | type == "string" and length > 0))))
  ' <<<"$response" >/dev/null; then
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

  # Keep the reply body off the command line. GitHub comment bodies can be
  # large enough that passing body=... to gh risks the OS argument-size limit.
  if ! jq -c '{body}' <<<"$reply_json" > "$reply_payload_file"; then
    echo "Failing comment $comment_id (could not build reply payload)" >&2
    failed=$((failed + 1))
    continue
  fi

  if gh api -X POST "repos/$owner/$repo/pulls/$pr_number/comments/$comment_id/replies" \
    --input "$reply_payload_file" >/dev/null; then
    echo "Posted reply to comment $comment_id"
    posted=$((posted + 1))
  else
    echo "Failed posting reply to comment $comment_id" >&2
    failed=$((failed + 1))
  fi
done < "$reply_iterator_file"

if [[ "$dry_run" == true && "$failed" -eq 0 ]]; then
  if [[ -n "$preview_file" ]]; then
    if ! cp "$canonical_preview_file" "$preview_file"; then
      echo "Failing approval preview (could not write: $preview_file)" >&2
      failed=$((failed + 1))
    else
      echo "DRY RUN ARTIFACT: $preview_file"
    fi
  else
    printf 'DRY RUN ARTIFACT: '
    cat "$canonical_preview_file"
  fi
  if [[ "$failed" -eq 0 ]]; then
    preview_digest="$(sha256_file "$canonical_preview_file")"
    echo "DRY RUN DIGEST: sha256:$preview_digest"
  fi
fi

echo "Summary: posted=$posted would_post=$would_post skipped=$skipped failed=$failed dry_run=$dry_run"

if [[ "$failed" -gt 0 ]]; then
  exit 2
fi
