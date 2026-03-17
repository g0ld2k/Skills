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
  { "comment_id": 12345, "body": "Reply text" }
]
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

fetch_script="$script_dir/fetch_unresolved_review_comments.sh"

if [[ ! -f "$fetch_script" || ! -r "$fetch_script" ]]; then
  die "Missing readable helper: $fetch_script"
fi

unresolved_ids="$(mktemp)"
tmp_unresolved="$(mktemp)"
trap 'rm -f "$tmp_unresolved" "$unresolved_ids"' EXIT

refresh_unresolved_ids() {
  bash "$fetch_script" "$owner" "$repo" "$pr_number" --output "$tmp_unresolved"
  jq -r '.[].comment_id' "$tmp_unresolved" | sed '/^null$/d' > "$unresolved_ids"
}

refresh_unresolved_ids

posted=0
would_post=0
skipped=0
failed=0

while IFS= read -r reply_json; do
  comment_id="$(jq -r '.comment_id // empty' <<<"$reply_json")"
  body="$(jq -r '.body // ""' <<<"$reply_json")"

  if [[ -z "$comment_id" || "$comment_id" == "null" ]]; then
    echo "Skipping entry without comment_id" >&2
    skipped=$((skipped + 1))
    continue
  fi

  # Use the unresolved snapshot fetched at start to avoid one API fetch per
  # reply. If state changes concurrently, rely on POST outcome and report it.
  if ! grep -qx "$comment_id" "$unresolved_ids"; then
    echo "Skipping comment $comment_id (resolved or not found in unresolved threads)"
    skipped=$((skipped + 1))
    continue
  fi

  if [[ "$dry_run" == true ]]; then
    echo "DRY RUN: would reply to comment $comment_id"
    would_post=$((would_post + 1))
    continue
  fi

  if gh api -X POST "repos/$owner/$repo/pulls/comments/$comment_id/replies" -f body="$body" >/dev/null; then
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
