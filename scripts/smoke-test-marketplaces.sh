#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is required for the marketplace smoke test" >&2
  exit 2
fi
if ! command -v copilot >/dev/null 2>&1; then
  echo "GitHub Copilot CLI is required for the marketplace smoke test" >&2
  exit 2
fi

codex_home="$(mktemp -d "${TMPDIR:-/tmp}/g0ld2k-codex-home.XXXXXX")"
copilot_home="$(mktemp -d "${TMPDIR:-/tmp}/g0ld2k-copilot-home.XXXXXX")"
trap 'rm -rf -- "$codex_home" "$copilot_home"' EXIT

codex() {
  CODEX_HOME="$codex_home" command codex "$@"
}

copilot() {
  COPILOT_HOME="$copilot_home" COPILOT_CACHE_HOME="$copilot_home/cache" command copilot "$@"
}

codex plugin marketplace add "$root" --json >"$codex_home/add.json"
codex plugin list --available --json >"$codex_home/available.json"
python3 - "$codex_home/available.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
names = [entry["name"] for entry in data["available"]]
if names != ["g0ld2k-skills"]:
    raise SystemExit(f"unexpected Codex marketplace entries: {names}")
PY
codex plugin add g0ld2k-skills@g0ld2k-skills --json >"$codex_home/install.json"

copilot plugin marketplace add "$root"
copilot plugin marketplace browse g0ld2k-skills >"$copilot_home/available.txt"
python3 - "$copilot_home/available.txt" <<'PY'
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    entries = [line.strip() for line in handle if line.startswith("  • ")]
if len(entries) != 1 or not entries[0].startswith("• g0ld2k-skills - "):
    raise SystemExit(f"unexpected Copilot marketplace entries: {entries}")
PY
copilot plugin install g0ld2k-skills@g0ld2k-skills

echo "Marketplace smoke test passed for Codex and GitHub Copilot."
