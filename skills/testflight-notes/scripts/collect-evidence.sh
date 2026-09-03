#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: collect-evidence.sh [--repo PATH] [--start REF | --cutoff-epoch SECONDS]

Prints a temporary evidence-directory path on success. The directory contains:
  head_oid                  frozen HEAD commit
  selection                 start<TAB>ref<TAB>oid or cutoff<TAB>epoch
  oids                      selected commit OIDs, oldest first
  commits/<oid>/message.z   OID, subject, and body as NUL records
  commits/<oid>/paths.z     changed paths as NUL records
  commits/<oid>/path-N      exact bytes for path N
  commits/<oid>/patch-N     patch limited to path N
  commits/<oid>/meta        comparison base, commit kind, and path count

The caller owns deletion of the returned directory.
EOF
}

repo="."
start_ref=""
cutoff_epoch=""

while (($#)); do
  case "$1" in
    --repo)
      (($# >= 2)) || { usage >&2; exit 2; }
      repo="$2"
      shift 2
      ;;
    --start)
      (($# >= 2)) || { usage >&2; exit 2; }
      start_ref="$2"
      shift 2
      ;;
    --cutoff-epoch)
      (($# >= 2)) || { usage >&2; exit 2; }
      cutoff_epoch="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'ERROR: unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -n "$start_ref" && -n "$cutoff_epoch" ]]; then
  printf 'ERROR: --start and --cutoff-epoch are mutually exclusive\n' >&2
  exit 2
fi
if [[ -n "$cutoff_epoch" && ! "$cutoff_epoch" =~ ^[0-9]+$ ]]; then
  printf 'ERROR: cutoff epoch must be a positive integer\n' >&2
  exit 2
fi

evidence_dir="$(mktemp -d "${TMPDIR:-/tmp}/testflight-evidence.XXXXXX")"
cleanup_on_exit() {
  status=$?
  trap - EXIT
  if ((status != 0)); then
    rm -rf -- "$evidence_dir"
    printf 'ERROR: evidence collection failed\n' >&2
  fi
  exit "$status"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

safe_git=(git -C "$repo" --no-pager --no-replace-objects -c color.ui=false -c log.showSignature=false)
repo_root="$("${safe_git[@]}" rev-parse --show-toplevel)"
safe_git=(git -C "$repo_root" --no-pager --no-replace-objects -c color.ui=false -c log.showSignature=false)

head_oid="$("${safe_git[@]}" rev-parse --verify --end-of-options 'HEAD^{commit}')"
printf '%s\n' "$head_oid" >"$evidence_dir/head_oid"

shallow="$("${safe_git[@]}" rev-parse --is-shallow-repository)"
if [[ "$shallow" == "true" ]]; then
  printf 'ERROR: shallow repository; fetch complete history before generating notes\n' >&2
  exit 1
fi
if [[ "$shallow" != "false" ]]; then
  printf 'ERROR: unrecognized shallow-repository result: %s\n' "$shallow" >&2
  exit 1
fi

selector=()
if [[ -n "$start_ref" ]]; then
  resolved_start="$start_ref"
  if "${safe_git[@]}" show-ref --verify --quiet "refs/tags/$start_ref"; then
    resolved_start="refs/tags/$start_ref"
  fi
  start_oid="$("${safe_git[@]}" rev-parse --verify --end-of-options "${resolved_start}^{commit}")"
  if ! "${safe_git[@]}" merge-base --is-ancestor "$start_oid" "$head_oid"; then
    printf 'ERROR: start ref is not an ancestor of frozen HEAD\n' >&2
    exit 1
  fi
  selector=("$start_oid..$head_oid")
  printf 'start\t%s\t%s\n' "$resolved_start" "$start_oid" >"$evidence_dir/selection"
elif [[ -n "$cutoff_epoch" ]]; then
  ((cutoff_epoch > 0)) || { printf 'ERROR: cutoff epoch must be positive\n' >&2; exit 2; }
  selector=("--since-as-filter=@$cutoff_epoch" "$head_oid")
  printf 'cutoff\t%s\n' "$cutoff_epoch" >"$evidence_dir/selection"
else
  if latest_tag="$("${safe_git[@]}" describe --tags --abbrev=0 "$head_oid" 2>/dev/null)"; then
    resolved_start="refs/tags/$latest_tag"
    start_oid="$("${safe_git[@]}" rev-parse --verify --end-of-options "${resolved_start}^{commit}")"
    selector=("$start_oid..$head_oid")
    printf 'start\t%s\t%s\n' "$resolved_start" "$start_oid" >"$evidence_dir/selection"
  else
    head_epoch="$("${safe_git[@]}" show -s --format=%ct "$head_oid")"
    cutoff_epoch=$((head_epoch - 14 * 24 * 60 * 60))
    ((cutoff_epoch > 0)) || cutoff_epoch=1
    selector=("--since-as-filter=@$cutoff_epoch" "$head_oid")
    printf 'cutoff\t%s\n' "$cutoff_epoch" >"$evidence_dir/selection"
  fi
fi

"${safe_git[@]}" rev-list --reverse "${selector[@]}" >"$evidence_dir/oids"
mkdir "$evidence_dir/commits"
empty_tree="$("${safe_git[@]}" mktree </dev/null)"

while IFS= read -r oid; do
  [[ "$oid" =~ ^[0-9a-fA-F]{40,64}$ ]] || {
    printf 'ERROR: invalid enumerated OID: %s\n' "$oid" >&2
    exit 1
  }
  commit_dir="$evidence_dir/commits/$oid"
  mkdir "$commit_dir"
  "${safe_git[@]}" show -s --format='%H%x00%s%x00%b%x00' "$oid" >"$commit_dir/message.z"

  parent_record="$("${safe_git[@]}" rev-list --parents -n 1 "$oid")"
  IFS=' ' read -r -a lineage <<<"$parent_record"
  if ((${#lineage[@]} == 1)); then
    comparison_base="$empty_tree"
    commit_kind="root"
  else
    comparison_base="${lineage[1]}"
    commit_kind="commit"
    ((${#lineage[@]} == 2)) || commit_kind="merge-first-parent"
  fi

  "${safe_git[@]}" diff --no-color --no-ext-diff --no-textconv \
    --name-only -z --find-renames --find-copies \
    "$comparison_base" "$oid" -- >"$commit_dir/paths.z"

  path_index=0
  while IFS= read -r -d '' path; do
    ((path_index += 1))
    printf -v suffix '%06d' "$path_index"
    printf '%s' "$path" >"$commit_dir/path-$suffix"
    "${safe_git[@]}" diff --no-color --no-ext-diff --no-textconv \
      "$comparison_base" "$oid" -- ":(literal)$path" >"$commit_dir/patch-$suffix"
  done <"$commit_dir/paths.z"

  printf 'base\t%s\nkind\t%s\npaths\t%s\n' \
    "$comparison_base" "$commit_kind" "$path_index" >"$commit_dir/meta"
done <"$evidence_dir/oids"

trap - EXIT INT TERM
printf '%s\n' "$evidence_dir"
