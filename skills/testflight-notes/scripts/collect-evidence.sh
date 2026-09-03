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
  commits/<oid>/changes.z   status plus one/two paths as NUL records
  commits/<oid>/paths.z     every changed path as NUL records
  commits/<oid>/path-N*     exact path bytes for change N
  commits/<oid>/meta        comparison base, kind, change/path counts
  objects-dir.z             source object directory as one NUL record

Generate a path-bound patch only when needed with render-evidence-patch.sh.
Copy detection is best effort; unchanged sources are not exhaustively scanned.

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

safe_git=(git -C "$repo" --no-pager --no-replace-objects -c color.ui=false \
  -c log.showSignature=false -c i18n.logOutputEncoding=UTF-8)
repo_root="$("${safe_git[@]}" rev-parse --show-toplevel)"
safe_git=(git -C "$repo_root" --no-pager --no-replace-objects -c color.ui=false \
  -c log.showSignature=false -c i18n.logOutputEncoding=UTF-8)

head_oid="$("${safe_git[@]}" rev-parse --verify --end-of-options 'HEAD^{commit}')"
printf '%s\n' "$head_oid" >"$evidence_dir/head_oid"

objects_dir="$("${safe_git[@]}" rev-parse --path-format=absolute --git-path objects)"
printf '%s\0' "$objects_dir" >"$evidence_dir/objects-dir.z"
object_format="$("${safe_git[@]}" rev-parse --show-object-format)"
isolated_git_dir="$evidence_dir/isolated.git"
git init --bare -q --object-format="$object_format" "$isolated_git_dir"
diff_git=(git --git-dir="$isolated_git_dir" --no-pager --no-replace-objects \
  -c color.ui=false -c core.attributesFile=/dev/null)
run_diff_git() {
  GIT_CONFIG_NOSYSTEM=1 GIT_ATTR_NOSYSTEM=1 GIT_ATTR_SOURCE="$head_oid" \
    GIT_OBJECT_DIRECTORY="$objects_dir" "${diff_git[@]}" "$@"
}

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
  tag_refs_file="$evidence_dir/tag-refs"
  tags_file="$evidence_dir/tags"
  "${safe_git[@]}" for-each-ref --format='%(refname)' refs/tags >"$tag_refs_file"
  : >"$tags_file"
  reachable_tag=false
  while IFS= read -r tag_ref; do
    [[ -n "$tag_ref" ]] || continue
    tag_oid="$("${safe_git[@]}" rev-parse --verify --end-of-options "$tag_ref")"
    tag_type="$("${safe_git[@]}" cat-file -t "$tag_oid")"
    if [[ "$tag_type" == tag ]]; then
      peeled_type="$("${safe_git[@]}" cat-file -t "${tag_oid}^{}")"
      [[ "$peeled_type" == commit ]] || continue
    elif [[ "$tag_type" != commit ]]; then
      continue
    fi
    tag_commit="$("${safe_git[@]}" rev-parse --verify --end-of-options "${tag_oid}^{commit}")"
    if "${safe_git[@]}" merge-base --is-ancestor "$tag_commit" "$head_oid"; then
      reachable_tag=true
      printf '%s\t%s\t%s\n' "$tag_ref" "$tag_oid" "$tag_commit" >>"$tags_file"
    else
      status=$?
      ((status == 1)) || exit "$status"
    fi
  done <"$tag_refs_file"
  if [[ "$reachable_tag" == true ]]; then
    while IFS=$'\t' read -r frozen_ref frozen_tag_oid _; do
      run_diff_git update-ref "$frozen_ref" "$frozen_tag_oid"
    done <"$tags_file"
    latest_tag="$(run_diff_git describe --tags --abbrev=0 "$head_oid")"
    resolved_start="refs/tags/$latest_tag"
    selection_record="$(awk -F '\t' -v ref="$resolved_start" '$1 == ref {print $2 "\t" $3}' "$tags_file")"
    [[ -n "$selection_record" && "$(printf '%s\n' "$selection_record" | wc -l | tr -d ' ')" == 1 ]] \
      || { printf 'ERROR: selected tag was not in the frozen candidate set\n' >&2; exit 1; }
    IFS=$'\t' read -r frozen_tag_oid start_oid <<<"$selection_record"
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
empty_tree="$("${safe_git[@]}" hash-object -t tree --stdin </dev/null)"

while IFS= read -r oid; do
  [[ "$oid" =~ ^[0-9a-fA-F]{40,64}$ ]] || {
    printf 'ERROR: invalid enumerated OID: %s\n' "$oid" >&2
    exit 1
  }
  commit_dir="$evidence_dir/commits/$oid"
  mkdir "$commit_dir"
  "${safe_git[@]}" show -s --format='format:%H%x00%s%x00%b%x00' "$oid" >"$commit_dir/message.z"

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

  run_diff_git diff --no-color --no-ext-diff --no-textconv \
    --ignore-submodules=none --name-status -z --find-renames --find-copies -l0 \
    "$comparison_base" "$oid" -- >"$commit_dir/changes.z"
  raw_file="$commit_dir/objects.z"
  run_diff_git diff --no-color --no-ext-diff --no-textconv \
    --ignore-submodules=none --raw -z --no-abbrev --find-renames --find-copies -l0 \
    "$comparison_base" "$oid" -- >"$raw_file"
  while IFS= read -r -d '' raw_header <&3; do
    IFS=' ' read -r old_mode new_mode old_object new_object raw_status <<<"$raw_header"
    old_mode="${old_mode#:}"
    IFS= read -r -d '' _ <&3
    if [[ "$raw_status" == R* || "$raw_status" == C* ]]; then
      IFS= read -r -d '' _ <&3
    fi
    if [[ "$old_mode" != 000000 && "$old_mode" != 160000 ]]; then
      run_diff_git cat-file -e "$old_object"
    fi
    if [[ "$new_mode" != 000000 && "$new_mode" != 160000 ]]; then
      run_diff_git cat-file -e "$new_object"
    fi
  done 3<"$raw_file"
  : >"$commit_dir/paths.z"

  change_index=0
  path_count=0
  while IFS= read -r -d '' change_status; do
    IFS= read -r -d '' first_path
    ((change_index += 1))
    ((path_count += 1))
    printf -v suffix '%06d' "$change_index"
    printf '%s\0' "$first_path" >>"$commit_dir/paths.z"
    if [[ "$change_status" == R* || "$change_status" == C* ]]; then
      IFS= read -r -d '' second_path
      ((path_count += 1))
      printf '%s\0' "$first_path" >"$commit_dir/path-$suffix-from"
      printf '%s\0' "$second_path" >"$commit_dir/path-$suffix-to"
      printf '%s\0' "$second_path" >>"$commit_dir/paths.z"
    else
      printf '%s\0' "$first_path" >"$commit_dir/path-$suffix"
    fi
    printf '%s\n' "$change_status" >"$commit_dir/status-$suffix"
  done <"$commit_dir/changes.z"

  printf 'base\t%s\nkind\t%s\nchanges\t%s\npaths\t%s\n' \
    "$comparison_base" "$commit_kind" "$change_index" "$path_count" >"$commit_dir/meta"
done <"$evidence_dir/oids"

trap - EXIT INT TERM
printf '%s\n' "$evidence_dir"
