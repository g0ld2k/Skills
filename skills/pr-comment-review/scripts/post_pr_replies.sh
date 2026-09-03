#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"

usage() {
  echo "Usage: $0 --owner <owner> --repo <repo> --pr <number> --replies-file <file> [--dry-run] [--preview-file <file>] [--approved-digest <sha256:...>]"
}

owner=""; repo=""; pr_number=""; replies_file=""
preview_file=""; approved_digest=""; dry_run=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner) owner="${2:-}"; shift 2 ;;
    --repo) repo="${2:-}"; shift 2 ;;
    --pr) pr_number="${2:-}"; shift 2 ;;
    --replies-file) replies_file="${2:-}"; shift 2 ;;
    --preview-file) preview_file="${2:-}"; shift 2 ;;
    --approved-digest) approved_digest="${2:-}"; shift 2 ;;
    --dry-run) dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$owner" && -n "$repo" && -n "$pr_number" && -n "$replies_file" ]] \
  || { usage >&2; exit 1; }
[[ "$pr_number" =~ ^[1-9][0-9]*$ ]] || die "PR number must be a positive integer"
[[ -f "$replies_file" ]] || die "Replies file not found: $replies_file"
if [[ "$dry_run" == false ]]; then
  [[ -f "$preview_file" && "$approved_digest" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "posting requires a preview file and its approved sha256 digest"
fi

require_cmd gh
require_cmd jq
require_cmd awk

if command -v shasum >/dev/null 2>&1; then
  sha256_tool="shasum"
elif command -v sha256sum >/dev/null 2>&1; then
  sha256_tool="sha256sum"
else
  die "a SHA-256 utility is required"
fi

sha256_file() {
  if [[ "$sha256_tool" == "shasum" ]]; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/pr-review-post.XXXXXX")"
cleanup() { rm -rf "$work_dir"; }
trap cleanup EXIT
requested_file="$work_dir/requested.json"
canonical_file="$work_dir/preview.json"
unresolved_file="$work_dir/unresolved.json"
iterator_file="$work_dir/replies.ndjson"
payload_file="$work_dir/payload.json"
approved_state_file="$work_dir/approved-state.json"
current_state_file="$work_dir/current-state.json"

# Snapshot the target and reply bytes once.
jq -sce --arg owner "$owner" --arg repo "$repo" --argjson pr "$pr_number" '
  def positive_integer: type == "number" and . > 0 and floor == .;
  if length == 1 and (.[0] | type == "array") and (.[0] | all(.[];
      type == "object"
      and (.thread_id | type == "string" and length > 0)
      and (.comment_id | positive_integer)
      and (.body | type == "string" and length > 0)))
  then {owner: $owner, repo: $repo, pr: $pr,
        replies: [.[0][] | {thread_id, comment_id, body}]}
  else error("invalid replies file") end
' "$replies_file" > "$requested_file" \
  || { echo "Failing replies file (each entry requires thread_id, positive-integer comment_id, and nonempty string body)" >&2; exit 2; }

if [[ "$dry_run" == false ]]; then
  cp "$preview_file" "$canonical_file" \
    || { echo "Failing approval preview (could not snapshot artifact)" >&2; exit 2; }
  actual_digest="sha256:$(sha256_file "$canonical_file")"
  [[ "$actual_digest" == "$approved_digest" ]] \
    || { echo "Failing approval preview (digest does not cover the supplied artifact)" >&2; exit 2; }
  jq -e --slurpfile requested "$requested_file" '
    type == "object"
    and (.owner == $requested[0].owner)
    and (.repo == $requested[0].repo)
    and (.pr == $requested[0].pr)
    and ([.replies[] | {thread_id, comment_id, body}] == $requested[0].replies)
    and all(.replies[];
      (.thread_state == null)
      or ((.thread_state | type == "object")
          and (.thread_state.root | type == "object")
          and (.thread_state.replies | type == "array")))
  ' "$canonical_file" >/dev/null \
    || { echo "Failing approval preview (artifact differs from current target or replies)" >&2; exit 2; }
fi

refresh_inventory() {
  bash "$script_dir/fetch_unresolved_review_comments.sh" "$owner" "$repo" "$pr_number" --output "$unresolved_file" \
    || { echo "Failing replies file (could not fetch complete current inventory)" >&2; return 2; }
  jq -e --slurpfile unresolved "$unresolved_file" '
    [.replies[] | {thread_id, comment_id}] as $provided
    | [$unresolved[0][] | {thread_id, comment_id}] as $required
    | ($provided | length) == ($provided | unique_by(.thread_id) | length)
      and (($required - $provided) | length == 0)
  ' "$requested_file" >/dev/null \
    || { echo "Failing replies file (reply inventory does not match current unresolved top-level review comments)" >&2; return 2; }
}

refresh_inventory || exit 2

if [[ "$dry_run" == true ]]; then
  jq -ce --slurpfile unresolved "$unresolved_file" '
    . as $requested
    | {owner, repo, pr,
       replies: [$requested.replies[] as $reply
         | [$unresolved[0][]
             | select(.thread_id == $reply.thread_id and .comment_id == $reply.comment_id)] as $matches
         | if ($matches | length) > 1 then error("duplicate inventory target")
           elif ($matches | length) == 0 then $reply + {thread_state: null}
           else $reply + {thread_state: ($matches[0] | {
             root: {author, path, line, body, created_at}, replies: (.replies // [])
           })} end]}
  ' "$requested_file" > "$canonical_file" \
    || { echo "Failing replies file (could not bind preview to thread content)" >&2; exit 2; }
fi

jq -c '.replies[]' "$canonical_file" > "$iterator_file" \
  || { echo "Failing replies file (could not enumerate replies)" >&2; exit 2; }

thread_state() {
  local thread_id="$1" comment_id="$2" response_file="$work_dir/thread.json"
  gh api graphql -f query='query($id:ID!){node(id:$id){... on PullRequestReviewThread{isResolved pullRequest{number repository{owner{login} name}} comments(first:100){nodes{databaseId replyTo{id}}}}}}' \
    -F id="$thread_id" > "$response_file" || return 20
  jq -e --arg owner "$owner" --arg repo "$repo" --argjson pr "$pr_number" --argjson cid "$comment_id" '
    type == "object"
    and ((has("errors") | not) or (.errors | type == "array" and length == 0))
    and (.data.node.isResolved | type == "boolean")
    and (.data.node.pullRequest.number == $pr)
    and ((.data.node.pullRequest.repository.owner.login | ascii_downcase) == ($owner | ascii_downcase))
    and ((.data.node.pullRequest.repository.name | ascii_downcase) == ($repo | ascii_downcase))
    and ([.data.node.comments.nodes[] | select(.databaseId == $cid and .replyTo == null)] | length == 1)
  ' "$response_file" >/dev/null || return 20
  [[ "$(jq -r '.data.node.isResolved' "$response_file")" == false ]] || return 10
}

verify_thread_state() {
  local reply="$1" thread_id="$2" comment_id="$3" match_count rc
  match_count="$(jq --arg tid "$thread_id" --argjson cid "$comment_id" \
    '[.[] | select(.thread_id == $tid and .comment_id == $cid)] | length' "$unresolved_file")" \
    || return 20
  if [[ "$match_count" == 1 ]]; then
    jq -ce --arg tid "$thread_id" --argjson cid "$comment_id" '
      [.[] | select(.thread_id == $tid and .comment_id == $cid)][0]
      | {root: {author, path, line, body, created_at}, replies: (.replies // [])}
    ' "$unresolved_file" > "$current_state_file" || return 20
    jq -ce '.thread_state | select(. != null)' <<<"$reply" > "$approved_state_file" \
      || return 20
    cmp -s "$approved_state_file" "$current_state_file" || return 20
  elif [[ "$match_count" != 0 ]]; then
    return 20
  fi

  rc=0
  thread_state "$thread_id" "$comment_id" || rc=$?
  if [[ "$match_count" == 0 && $rc -eq 0 ]]; then
    return 20
  fi
  return "$rc"
}

posted=0; would_post=0; skipped=0; failed=0; aborted=false
while IFS= read -r reply; do
  thread_id="$(jq -r '.thread_id' <<<"$reply")"
  comment_id="$(jq -r '.comment_id' <<<"$reply")"
  if [[ "$dry_run" == false ]]; then
    if ! refresh_inventory; then
      failed=$((failed + 1))
      aborted=true
      break
    fi
  fi
  rc=0
  verify_thread_state "$reply" "$thread_id" "$comment_id" || rc=$?
  if [[ $rc -eq 10 ]]; then
    echo "Skipping comment $comment_id (thread $thread_id already resolved)"
    skipped=$((skipped + 1))
    continue
  elif [[ $rc -ne 0 ]]; then
    echo "Failing comment $comment_id (fresh thread check failed)" >&2
    failed=$((failed + 1))
    aborted=true
    break
  fi

  if [[ "$dry_run" == true ]]; then
    echo "DRY RUN: would reply to comment $comment_id"
    would_post=$((would_post + 1))
    continue
  fi

  if ! jq -c '{body}' <<<"$reply" > "$payload_file"; then
    echo "Failing comment $comment_id (could not build payload)" >&2
    failed=$((failed + 1)); aborted=true; break
  fi
  if gh api -X POST "repos/$owner/$repo/pulls/$pr_number/comments/$comment_id/replies" --input "$payload_file" >/dev/null; then
    echo "Posted reply to comment $comment_id"
    posted=$((posted + 1))
  else
    echo "Failed posting reply to comment $comment_id" >&2
    failed=$((failed + 1))
    aborted=true
    break
  fi
done < "$iterator_file"

if [[ "$dry_run" == true && $failed -eq 0 ]]; then
  if [[ -n "$preview_file" ]]; then
    cp "$canonical_file" "$preview_file" || { echo "Could not write approval preview" >&2; exit 2; }
    echo "DRY RUN ARTIFACT: $preview_file"
  else
    printf 'DRY RUN ARTIFACT: '
    cat "$canonical_file"
    echo
  fi
  echo "DRY RUN DIGEST: sha256:$(sha256_file "$canonical_file")"
fi

echo "Summary: posted=$posted would_post=$would_post skipped=$skipped failed=$failed dry_run=$dry_run"
[[ "$aborted" == false && $failed -eq 0 ]] || exit 2
