#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/common.sh"

usage() {
  cat <<USAGE
Usage: $0 --input <unresolved-comments.json> [--output <triage.md>]

Generate a markdown triage template from unresolved review comments JSON.
USAGE
}

input_file=""
output_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      input_file="${2:-}"
      shift 2
      ;;
    --output)
      output_file="${2:-}"
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

if [[ -z "$input_file" ]]; then
  usage >&2
  exit 1
fi

require_cmd jq

if [[ ! -f "$input_file" ]]; then
  die "Input file not found: $input_file"
fi

content="$({
  echo "# PR Comment Triage"
  echo
  echo "Generated from unresolved review threads only."
  echo
  jq -r '
    if length == 0 then
      "No unresolved top-level review comments found."
    else
      to_entries[]
      | (.value.line // "n/a") as $line
      | "## Comment #\(.value.comment_id) [\(.value.path):\($line)]\n"
        + "- URL: \(.value.url)\n"
        + "- Validity: <valid|partial|invalid>\n"
        + "- Priority: <high|medium|low>\n"
        + "- Decision: <fix|reply|discuss>\n"
        + "- Planned action: <fill>\n"
        + "- Draft reply: <fill>\n"
    end
  ' "$input_file"
} )"

if [[ -n "$output_file" ]]; then
  printf '%s\n' "$content" > "$output_file"
else
  printf '%s\n' "$content"
fi
