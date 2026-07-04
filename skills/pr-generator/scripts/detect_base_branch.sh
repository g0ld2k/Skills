#!/usr/bin/env bash
set -euo pipefail

base_branch="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)"

if [[ -z "${base_branch}" ]]; then
  if git show-ref --verify --quiet refs/remotes/origin/main; then
    base_branch="main"
  elif git show-ref --verify --quiet refs/remotes/origin/master; then
    base_branch="master"
  fi
fi

if [[ -n "${base_branch}" ]]; then
  printf '%s\n' "${base_branch}"
fi
