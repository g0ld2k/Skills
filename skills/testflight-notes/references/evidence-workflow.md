# Deterministic Git Evidence Workflow

Use this workflow before classifying or writing TestFlight notes. Completion
requires one pinned history selector, successful metadata and path collection,
and targeted patch evidence for every claim that metadata alone cannot prove.

## Inputs and Bounds

- Resolve the repository from the current working directory.
- Accept either a timeframe or a starting ref/tag, never both.
- Accept timeframes only as `last <N> day(s)`, `last <N> week(s)`,
  `<N> day(s) ago`, or `<N> week(s) ago`, optionally prefixed with `since `.
  `N` is a positive decimal integer without a leading zero. Reject other
  natural-language and ISO-date forms.
- Read `MAX_NOTES_CHARACTERS` from repository/environment configuration. Its
  default is 4000 and its minimum is 93, the length of the mandatory empty
  result. This is a repository budget, not an asserted TestFlight API limit.
- When the caller supplies no selector, use the latest tag reachable from
  pinned `HEAD`; if none exists, use a normalized 14-day selector.

## 1. Pin the Repository Surface

~~~bash
repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  printf '%s\n' 'ERROR: current directory is not a Git work tree.' >&2
  exit 2
}
head_sha="$(git -C "$repo_root" rev-parse --verify --end-of-options HEAD^{commit})" || {
  printf '%s\n' 'ERROR: HEAD is not a resolvable commit.' >&2
  exit 2
}
object_id_length="${#head_sha}"
shallow="$(git -C "$repo_root" rev-parse --is-shallow-repository 2>/dev/null)" || {
  printf '%s\n' 'ERROR: could not determine whether Git history is shallow.' >&2
  exit 2
}
if [[ "$shallow" == true ]]; then
  printf '%s\n' \
    'ERROR: selected history is shallow; fetch complete history before generating notes.' \
    >&2
  exit 2
fi
~~~

Record `repo_root`, `head_sha`, and `object_id_length` in the run ledger. The
pinned SHA remains the end of the run even if the checked-out branch moves
later. Deriving the object-ID length from that full SHA supports both SHA-1 and
SHA-256 repositories.

## 2. Validate Configuration

~~~bash
max_notes_characters="${MAX_NOTES_CHARACTERS:-4000}"
min_notes_characters=93
if [[ ! "$max_notes_characters" =~ ^[1-9][0-9]*$ ]]; then
  printf 'ERROR: MAX_NOTES_CHARACTERS must be an integer of at least %s; received: %s\n' \
    "$min_notes_characters" "$max_notes_characters" >&2
  exit 2
fi
if (( ${#max_notes_characters} > 4 )); then
  target_notes_characters=3800
elif (( max_notes_characters < min_notes_characters )); then
  printf 'ERROR: MAX_NOTES_CHARACTERS must be an integer of at least %s; received: %s\n' \
    "$min_notes_characters" "$max_notes_characters" >&2
  exit 2
elif (( max_notes_characters < 3800 )); then
  target_notes_characters="$max_notes_characters"
else
  target_notes_characters=3800
fi
~~~

Record the validated maximum and target in the run ledger.

## 3. Normalize One Immutable Selector

Normalize a timeframe once, convert it once to Git's epoch argument, and pair
that argument with pinned `head_sha`:

~~~bash
normalize_timeframe() {
  local raw="$1"
  local last_pattern='^(since )?last ([1-9][0-9]*) (day|days|week|weeks)$'
  local ago_pattern='^(since )?([1-9][0-9]*) (day|days|week|weeks) ago$'
  if [[ "$raw" =~ $last_pattern ]]; then
    printf '%s %s ago\n' "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
  elif [[ "$raw" =~ $ago_pattern ]]; then
    printf '%s %s ago\n' "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
  else
    return 1
  fi
}

pin_timeframe() {
  local raw="$1"
  local cutoff_epoch current_epoch
  normalized_timeframe="$(normalize_timeframe "$raw")" || {
    printf '%s\n' \
      'ERROR: timeframe must be last <positive integer> day(s)|week(s), or <positive integer> day(s)|week(s) ago, with an optional since prefix.' \
      >&2
    printf 'Received: %s\n' "$raw" >&2
    return 2
  }
  max_age_arg="$(git -C "$repo_root" rev-parse --since="$normalized_timeframe")" || {
    printf 'ERROR: Git could not normalize timeframe: %s\n' \
      "$normalized_timeframe" >&2
    return 2
  }
  if [[ ! "$max_age_arg" =~ ^--max-age=[0-9]+$ ]]; then
    printf 'ERROR: Git returned an invalid timeframe selector: %s\n' \
      "$max_age_arg" >&2
    return 2
  fi
  cutoff_epoch="${max_age_arg#--max-age=}"
  current_epoch="$(date +%s)" || {
    printf '%s\n' 'ERROR: could not read the current Unix epoch.' >&2
    return 2
  }
  if [[ ! "$current_epoch" =~ ^[0-9]+$ ]]; then
    printf 'ERROR: current Unix epoch is invalid: %s\n' \
      "$current_epoch" >&2
    return 2
  fi
  if (( ${#cutoff_epoch} > ${#current_epoch} )) ||
    { (( ${#cutoff_epoch} == ${#current_epoch} )) &&
      [[ "$cutoff_epoch" > "$current_epoch" ]]; }; then
    printf 'ERROR: timeframe resolves to an impossible future cutoff: %s\n' \
      "$normalized_timeframe" >&2
    return 2
  fi
  since_filter_arg="--since-as-filter=$cutoff_epoch"
  history_selector=("$since_filter_arg" "$head_sha")
}
~~~

`--since-as-filter` preserves the pinned cutoff while visiting the complete
reachable history. Do not retain the intermediate `--max-age` argument, which
may stop traversal at an older commit before reaching a newer-dated ancestor.
The current epoch is only a bound check; Git's single normalized cutoff remains
the selector source of truth.

Choose one branch and never recompute it:

~~~bash
if [[ -n "${timeframe:-}" && -n "${start_ref:-}" ]]; then
  printf '%s\n' 'ERROR: provide a timeframe or a starting ref, not both.' >&2
  exit 2
elif [[ -n "${timeframe:-}" ]]; then
  pin_timeframe "$timeframe" || exit $?
  selector_kind=timeframe
  selector_label="$normalized_timeframe ($since_filter_arg $head_sha)"
elif [[ -n "${start_ref:-}" ]]; then
  if [[ "$start_ref" == refs/* ]]; then
    start_revision="${start_ref}^{commit}"
  else
    tag_ref="refs/tags/$start_ref"
    if git -C "$repo_root" show-ref --verify --quiet "$tag_ref"; then
      start_revision="${tag_ref}^{commit}"
    else
      tag_lookup_status=$?
      if (( tag_lookup_status != 1 )); then
        printf 'ERROR: Git could not check tag namespace for: %s\n' \
          "$start_ref" >&2
        exit 2
      fi
      start_revision="${start_ref}^{commit}"
    fi
  fi
  start_sha="$(git -C "$repo_root" rev-parse \
    --verify --end-of-options "$start_revision")" || {
    printf 'ERROR: ref or tag is unavailable or does not name a commit: %s\n' \
      "$start_ref" >&2
    exit 2
  }
  if merge_base_error="$(git -C "$repo_root" merge-base \
    --is-ancestor "$start_sha" "$head_sha" 2>&1)"; then
    :
  else
    merge_base_status=$?
    if (( merge_base_status == 1 )); then
      printf 'ERROR: starting ref %s is not an ancestor of pinned HEAD %s; choose a ref on this history.\n' \
        "$start_ref" "$head_sha" >&2
    else
      printf 'ERROR: Git could not verify ancestry for %s and %s: %s\n' \
        "$start_sha" "$head_sha" "$merge_base_error" >&2
    fi
    exit 2
  fi
  history_selector=("$start_sha..$head_sha")
  selector_kind=revision-range
  selector_label="$start_sha..$head_sha"
else
  if ! reachable_tags="$(git -C "$repo_root" for-each-ref \
    --merged="$head_sha" --format='%(refname:short)' refs/tags 2>&1)"; then
    printf 'ERROR: Git could not inspect tags reachable from pinned HEAD: %s\n' \
      "$reachable_tags" >&2
    exit 2
  fi
  if [[ -n "$reachable_tags" ]]; then
    if ! latest_tag="$(git -C "$repo_root" describe \
      --tags --abbrev=0 "$head_sha" 2>&1)"; then
      printf 'ERROR: Git found reachable tags but could not select the latest one: %s\n' \
        "$latest_tag" >&2
      exit 2
    fi
    tag_sha="$(git -C "$repo_root" rev-parse \
      --verify --end-of-options "refs/tags/${latest_tag}^{commit}")" || {
      printf 'ERROR: latest reachable tag cannot be resolved to a commit: %s\n' \
        "$latest_tag" >&2
      exit 2
    }
    history_selector=("$tag_sha..$head_sha")
    selector_kind=latest-tag-fallback
    selector_label="$latest_tag ($tag_sha..$head_sha)"
  else
    pin_timeframe '14 days ago' || exit $?
    selector_kind=timeframe-fallback
    selector_label="$normalized_timeframe ($since_filter_arg $head_sha)"
  fi
fi
readonly -a history_selector
~~~

For an unqualified start name, an exact tag wins over a colliding pseudo-ref,
branch, or other revision. A caller can still select a colliding non-tag by
supplying its fully qualified ref name.

Record the exact array, kind, label, and fallback assumption. A selector error
ends the run without a notes block.

## 4. Enumerate Once

~~~bash
selected_commits="$(git -C "$repo_root" --no-pager log \
  --no-show-signature --reverse "${history_selector[@]}" --format='%H')" || {
  printf '%s\n' 'ERROR: Git history enumeration failed.' >&2
  exit 2
}
~~~

Successful empty output is a valid empty range. Record that outcome before
classification. Every later history-consuming `git log` receives the exact
same `history_selector` array.

## 5. Capture Metadata and Paths

Keep intermediate evidence out of stdout and clean it up on exit:

~~~bash
evidence_dir="$(mktemp -d "${TMPDIR:-/tmp}/testflight-notes.XXXXXX")" || {
  printf '%s\n' 'ERROR: could not create a temporary evidence directory.' >&2
  exit 2
}
trap 'rm -rf -- "$evidence_dir"' EXIT
metadata_file="$evidence_dir/metadata"
name_status_file="$evidence_dir/name-status"
path_ledger_file="$evidence_dir/path-ledger"
patch_file="$evidence_dir/patch"
error_file="$evidence_dir/error"
~~~

Capture metadata as a flat sequence of six fields per commit—SHA, parents,
subject, body, author, and ISO timestamp—with NUL bytes between fields. Parse
the complete file in positional groups of six; empty parent/body fields remain
valid fields and there is no extra record delimiter.

~~~bash
if ! git -C "$repo_root" --no-pager log --no-show-signature --reverse \
  "${history_selector[@]}" \
  -z --pretty=format:'%H%x00%P%x00%s%x00%b%x00%an%x00%aI' \
  >"$metadata_file" 2>"$error_file"; then
  printf 'ERROR: Git metadata collection failed: %s\n' "$(<"$error_file")" >&2
  exit 2
fi
~~~

Capture NUL-delimited name-status records so paths remain data when they contain
whitespace or newlines. Force root and submodule evidence. Compare merge commits
with their first parent, but do not limit history traversal to the first-parent
chain:

~~~bash
if ! git -C "$repo_root" --no-pager log --no-show-signature --reverse \
  "${history_selector[@]}" --root --diff-merges=first-parent \
  --ignore-submodules=none --find-renames --find-copies --name-status -z \
  --pretty=format:'commit %H%x00' \
  >"$name_status_file" 2>"$error_file"; then
  printf 'ERROR: Git path collection failed: %s\n' "$(<"$error_file")" >&2
  exit 2
fi
~~~

Parse the file statefully. Record both paths for a rename or copy:

~~~bash
record_path_evidence() {
  printf '%s\0%s\0%s\0' "$1" "$2" "$3" >>"$path_ledger_file" || {
    printf '%s\n' 'ERROR: could not record path evidence.' >&2
    exit 2
  }
}

while IFS= read -r -d '' commit_record; do
  [[ -z "$commit_record" ]] && continue
  [[ "$commit_record" =~ ^commit\ ([0-9a-f]+)$ ]] || {
    printf 'ERROR: malformed commit record in path evidence: %s\n' \
      "$commit_record" >&2
    exit 2
  }
  evidence_sha="${BASH_REMATCH[1]}"
  if (( ${#evidence_sha} != object_id_length )); then
    printf 'ERROR: object ID has %s characters; expected %s: %s\n' \
      "${#evidence_sha}" "$object_id_length" "$evidence_sha" >&2
    exit 2
  fi

  while IFS= read -r -d '' status_record; do
    [[ -z "$status_record" ]] && break
    evidence_status="${status_record#$'\n'}"
    IFS= read -r -d '' evidence_path || {
      printf '%s\n' 'ERROR: missing path in name-status evidence.' >&2
      exit 2
    }
    record_path_evidence "$evidence_sha" "$evidence_status" "$evidence_path"

    if [[ "$evidence_status" == R* || "$evidence_status" == C* ]]; then
      IFS= read -r -d '' evidence_path || {
        printf '%s\n' 'ERROR: missing destination path in rename/copy evidence.' >&2
        exit 2
      }
      record_path_evidence "$evidence_sha" "$evidence_status" "$evidence_path"
    fi
  done
done <"$name_status_file"
~~~

## 6. Inspect Targeted Patches

After reading metadata and path records, group every ambiguous candidate row by
its exact path. Run one query per unique path, not one per candidate. Disable
configured color and single-path following so local settings do not alter the
patch evidence or pinned traversal:

~~~bash
if ! git -C "$repo_root" --no-pager log --no-show-signature --reverse \
  "${history_selector[@]}" --root --diff-merges=first-parent \
  --ignore-submodules=none --no-follow --no-color --no-ext-diff --no-textconv \
  --find-renames --find-copies \
  --patch --format='commit %H' -- ":(literal)$candidate_path" \
  >"$patch_file" 2>"$error_file"; then
  printf 'ERROR: targeted patch read failed for %s: %s\n' \
    "$candidate_path" "$(<"$error_file")" >&2
  exit 2
fi
~~~

Inspect only the `commit <sha>` records requested for that path group. For each
matching SHA/path, write a concise evidence summary to the ledger and discard
the raw patch before processing the next path. A missing requested record is an
evidence error, not permission to widen the selector or infer a claim.

## Completion Criteria

Return to `SKILL.md` only when all are true:

- The run ledger contains pinned `head_sha`, exact `history_selector`, selector
  kind/label, fallback assumption, and validated maximum/target budgets.
- Enumeration succeeded, including a recorded successful-empty outcome when
  applicable.
- Metadata and name-status collection succeeded with no intermediate output on
  stdout.
- Every candidate has exact SHA/path evidence.
- Every ambiguous tester effect or platform claim has a concise targeted-patch
  evidence row, and no raw patch is retained.
- Any Git, input, configuration, or shallow-history error ended the run with a
  useful non-zero `ERROR:` and no notes block.
