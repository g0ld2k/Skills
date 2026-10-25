#!/usr/bin/env bash
# Apply the GitHub setup proven on g0ld2k/Contadino to another repository.
# Every write is a PATCH or PUT, or an update of the existing default-branch
# ruleset, so rerunning a phase is safe.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  apply-github-setup.sh settings --repo OWNER/NAME [--dry-run]
  apply-github-setup.sh ruleset  --repo OWNER/NAME --ci-check CONTEXT [--ci-app-id ID] [--dry-run]
  apply-github-setup.sh verify   --repo OWNER/NAME --ci-check CONTEXT [--ci-app-id ID]

settings  merge options, Actions policy, read-only workflow token and the
          needs-human-verification label
ruleset   default-branch ruleset with required checks; refuses to run until the
          Label gate and PR title workflows are on the default branch
verify    compare the live repository with this setup; exits 1 on drift

--ci-app-id defaults to 117084 (Xcode Cloud).
EOF
}

GITHUB_ACTIONS_APP_ID=15368
LABEL=needs-human-verification
MANAGED_RULE_TYPES='["deletion","non_fast_forward","pull_request","required_linear_history","required_status_checks"]'

phase=${1:-}
[ $# -gt 0 ] && shift
repo=""
ci_check=""
ci_app_id=117084
dry_run=false
while [ $# -gt 0 ]; do
  case $1 in
    --repo) repo=${2:?--repo needs OWNER/NAME}; shift 2 ;;
    --ci-check) ci_check=${2:?--ci-check needs a check name}; shift 2 ;;
    --ci-app-id) ci_app_id=${2:?--ci-app-id needs an app id}; shift 2 ;;
    --dry-run) dry_run=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case $phase in
  settings | ruleset | verify) ;;
  -h | --help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac
[ -n "$repo" ] || { echo "--repo is required" >&2; exit 2; }
if [ "$phase" != settings ] && [ -z "$ci_check" ]; then
  echo "--ci-check is required for $phase" >&2
  exit 2
fi

repo_settings() {
  jq -n '{
    allow_squash_merge: true, allow_merge_commit: false, allow_rebase_merge: false,
    squash_merge_commit_title: "PR_TITLE", squash_merge_commit_message: "PR_BODY",
    delete_branch_on_merge: true, allow_update_branch: true, allow_auto_merge: true,
    has_wiki: false, has_projects: false
  }'
}
actions_permissions() { jq -n '{enabled: true, allowed_actions: "selected", sha_pinning_required: true}'; }
selected_actions() { jq -n '{github_owned_allowed: true, verified_allowed: false, patterns_allowed: []}'; }
workflow_permissions() { jq -n '{default_workflow_permissions: "read", can_approve_pull_request_reviews: false}'; }

ruleset_rules() {
  jq -n --arg ci "$ci_check" --argjson ci_app "$ci_app_id" --argjson gha "$GITHUB_ACTIONS_APP_ID" '[
    {type: "deletion"},
    {type: "non_fast_forward"},
    {type: "pull_request", parameters: {
      required_approving_review_count: 0, dismiss_stale_reviews_on_push: false,
      required_reviewers: [], require_code_owner_review: false,
      require_last_push_approval: false, required_review_thread_resolution: false,
      allowed_merge_methods: ["squash"]}},
    {type: "required_linear_history"},
    {type: "required_status_checks", parameters: {
      strict_required_status_checks_policy: false, do_not_enforce_on_create: false,
      required_status_checks: [
        {context: $ci, integration_id: $ci_app},
        {context: "Label gate", integration_id: $gha},
        {context: "PR title", integration_id: $gha}]}}
  ]'
}

# write METHOD ENDPOINT JSON
write() {
  if $dry_run; then
    printf 'would %s %s\n%s\n' "$1" "$2" "$3"
  else
    printf '%s' "$3" | gh api --method "$1" "$2" --input - >/dev/null
    echo "$1 $2"
  fi
}

default_branch() { gh api "repos/$repo" --jq .default_branch; }

# Prints the id of the repository ruleset that targets the default branch, or
# nothing. Fails when more than one does, since merging rules across them is
# a decision for the maintainer.
default_branch_ruleset_id() {
  local branch=$1 ids=() id
  for id in $(gh api --paginate "repos/$repo/rulesets" \
    --jq '.[] | select(.target == "branch" and .source_type == "Repository") | .id'); do
    if gh api "repos/$repo/rulesets/$id" --jq '.conditions.ref_name.include[]' |
      grep -qxF -e '~DEFAULT_BRANCH' -e "refs/heads/$branch" -e '~ALL'; then
      ids+=("$id")
    fi
  done
  if [ ${#ids[@]} -gt 1 ]; then
    echo "more than one ruleset targets $branch (${ids[*]}); merge them by hand first" >&2
    return 1
  fi
  [ ${#ids[@]} -eq 0 ] || echo "${ids[0]}"
}

apply_settings() {
  write PATCH "repos/$repo" "$(repo_settings)"
  write PUT "repos/$repo/actions/permissions" "$(actions_permissions)"
  write PUT "repos/$repo/actions/permissions/selected-actions" "$(selected_actions)"
  write PUT "repos/$repo/actions/permissions/workflow" "$(workflow_permissions)"
  local description="Blocks merging until the maintainer confirms the manual checks"
  if $dry_run; then
    echo "would create or update label $LABEL"
  else
    gh label create "$LABEL" --repo "$repo" --color fbca04 --description "$description" --force >/dev/null
    echo "label $LABEL"
  fi
}

apply_ruleset() {
  local branch id rules
  branch=$(default_branch)
  for workflow in pr-label-gate.yml pr-title.yml; do
    if ! gh api "repos/$repo/contents/.github/workflows/$workflow?ref=$branch" --silent 2>/dev/null; then
      echo ".github/workflows/$workflow is not on $branch yet. Merge the workflows PR first:" \
        "a required check that never reports blocks every PR." >&2
      exit 1
    fi
  done
  id=$(default_branch_ruleset_id "$branch")
  if [ -n "$id" ]; then
    # Keep rules this setup doesn't manage, such as required signatures.
    rules=$(gh api "repos/$repo/rulesets/$id" |
      jq --argjson managed "$MANAGED_RULE_TYPES" --argjson ours "$(ruleset_rules)" \
        '[.rules[] | select(.type as $t | $managed | index($t) | not)] + $ours')
    write PUT "repos/$repo/rulesets/$id" \
      "$(jq -n --argjson rules "$rules" '{enforcement: "active", rules: $rules}')"
  else
    write POST "repos/$repo/rulesets" "$(jq -n --argjson rules "$(ruleset_rules)" '{
      name: "Protect default branch", target: "branch", enforcement: "active",
      conditions: {ref_name: {include: ["~DEFAULT_BRANCH"], exclude: []}},
      bypass_actors: [], rules: $rules}')"
  fi
}

drift=0
# check NAME ENDPOINT EXPECTED_JSON: compares only the keys EXPECTED_JSON sets.
check() {
  local actual want
  want=$(jq -cS . <<<"$3")
  actual=$(gh api "$2" | jq -cS --argjson want "$want" 'with_entries(select(.key as $k | $want | has($k)))')
  if [ "$actual" = "$want" ]; then
    echo "ok     $1"
  else
    echo "drift  $1: $actual (want $want)"
    drift=1
  fi
}

# Reduces a rules array to what this setup decides.
RULES_SUMMARY='{
  types: ([.[].type | select(. as $t | $managed | index($t))] | sort),
  merge: (map(select(.type == "pull_request"))[0].parameters
    | {allowed_merge_methods: .allowed_merge_methods, required_approving_review_count: .required_approving_review_count}),
  checks: (map(select(.type == "required_status_checks"))[0].parameters
    | {strict: .strict_required_status_checks_policy,
       contexts: ((.required_status_checks // []) | map({context, integration_id}) | sort_by(.context))})
}'

verify() {
  check "repository settings" "repos/$repo" "$(repo_settings)"
  check "actions permissions" "repos/$repo/actions/permissions" "$(actions_permissions)"
  check "selected actions" "repos/$repo/actions/permissions/selected-actions" "$(selected_actions)"
  check "workflow token" "repos/$repo/actions/permissions/workflow" "$(workflow_permissions)"

  if gh api "repos/$repo/labels/$LABEL" --silent 2>/dev/null; then
    echo "ok     label $LABEL"
  else
    echo "drift  label $LABEL is missing"
    drift=1
  fi

  local id want actual
  id=$(default_branch_ruleset_id "$(default_branch)")
  want=$(ruleset_rules | jq -cS --argjson managed "$MANAGED_RULE_TYPES" "{enforcement: \"active\", rules: ($RULES_SUMMARY)}")
  if [ -z "$id" ]; then
    echo "drift  no ruleset targets the default branch"
    drift=1
  else
    actual=$(gh api "repos/$repo/rulesets/$id" | jq -cS --argjson managed "$MANAGED_RULE_TYPES" "{enforcement, rules: (.rules | $RULES_SUMMARY)}")
    if [ "$actual" = "$want" ]; then
      echo "ok     ruleset $id"
    else
      echo "drift  ruleset $id: $actual (want $want)"
      drift=1
    fi
  fi
  return $drift
}

case $phase in
  settings) apply_settings ;;
  ruleset) apply_ruleset ;;
  verify) verify ;;
esac
