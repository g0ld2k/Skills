#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: render-evidence-patch.sh --evidence-dir PATH --oid OID --change NUMBER"
}

evidence_dir=""
oid=""
change=""
while (($#)); do
  case "$1" in
    --evidence-dir) (($# >= 2)) || { usage >&2; exit 2; }; evidence_dir="$2"; shift 2 ;;
    --oid) (($# >= 2)) || { usage >&2; exit 2; }; oid="$2"; shift 2 ;;
    --change) (($# >= 2)) || { usage >&2; exit 2; }; change="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -d "$evidence_dir" && "$oid" =~ ^[0-9a-fA-F]{40,64}$ \
   && "$change" =~ ^[1-9][0-9]*$ ]] \
  || { printf 'ERROR: invalid evidence directory, OID, or change number\n' >&2; exit 2; }

printf -v suffix '%06d' "$change"
commit_dir="$evidence_dir/commits/$oid"
meta_file="$commit_dir/meta"
status_file="$commit_dir/status-$suffix"
[[ -d "$evidence_dir/isolated.git" && -f "$evidence_dir/head_oid" \
   && -f "$evidence_dir/objects-dir.z" && -f "$meta_file" && -f "$status_file" ]] \
  || { printf 'ERROR: incomplete evidence for requested change\n' >&2; exit 1; }

head_oid="$(<"$evidence_dir/head_oid")"
comparison_base="$(awk -F '\t' '$1 == "base" {print $2}' "$meta_file")"
[[ "$head_oid" =~ ^[0-9a-fA-F]{40,64}$ \
   && "$comparison_base" =~ ^[0-9a-fA-F]{40,64}$ ]] \
  || { printf 'ERROR: invalid pinned evidence OID\n' >&2; exit 1; }
objects_dir=""
IFS= read -r -d '' objects_dir <"$evidence_dir/objects-dir.z" \
  || { printf 'ERROR: invalid object-directory record\n' >&2; exit 1; }
[[ -n "$objects_dir" ]] || { printf 'ERROR: empty object-directory record\n' >&2; exit 1; }

pathspecs=()
if [[ -f "$commit_dir/path-$suffix" ]]; then
  first_path=""
  IFS= read -r -d '' first_path <"$commit_dir/path-$suffix" \
    || { printf 'ERROR: invalid path record\n' >&2; exit 1; }
  pathspecs+=(":(literal)$first_path")
elif [[ -f "$commit_dir/path-$suffix-from" && -f "$commit_dir/path-$suffix-to" ]]; then
  first_path=""; second_path=""
  IFS= read -r -d '' first_path <"$commit_dir/path-$suffix-from" \
    || { printf 'ERROR: invalid source-path record\n' >&2; exit 1; }
  IFS= read -r -d '' second_path <"$commit_dir/path-$suffix-to" \
    || { printf 'ERROR: invalid destination-path record\n' >&2; exit 1; }
  pathspecs+=(":(literal)$first_path" ":(literal)$second_path")
else
  printf 'ERROR: missing path record for requested change\n' >&2
  exit 1
fi

patch_file="$commit_dir/patch-$suffix"
temporary_patch="$(mktemp "$commit_dir/.patch-$suffix.XXXXXX")"
cleanup() { rm -f -- "$temporary_patch"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

diff_git=(git --git-dir="$evidence_dir/isolated.git" --no-pager \
  --no-replace-objects -c color.ui=false -c core.attributesFile=/dev/null)
GIT_CONFIG_NOSYSTEM=1 GIT_ATTR_NOSYSTEM=1 GIT_ATTR_SOURCE="$head_oid" \
  GIT_OBJECT_DIRECTORY="$objects_dir" "${diff_git[@]}" diff \
  --no-color --no-ext-diff --no-textconv --ignore-submodules=none \
  --find-renames --find-copies -l0 "$comparison_base" "$oid" -- \
  "${pathspecs[@]}" >"$temporary_patch"
mv -f -- "$temporary_patch" "$patch_file"
trap - EXIT INT TERM
printf '%s\n' "$patch_file"
