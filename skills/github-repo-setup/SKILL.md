---
name: github-repo-setup
description: Use when asked to apply the squash-only, ruleset-gated GitHub setup for agent-written PRs to a repository.
license: MIT
disable-model-invocation: true
---

# GitHub repo setup

Bring a repository to the setup proven on g0ld2k/Contadino: squash-only merges with the PR title and body as the commit, a default-branch ruleset gated on CI, `Label gate` and `PR title`, Actions limited to SHA-pinned GitHub-owned actions, and an `AGENTS.md` that tells agents the rules. [`scripts/apply-github-setup.sh`](scripts/apply-github-setup.sh) makes the API changes; every phase is safe to rerun and takes `--dry-run`.

The ruleset goes on last. A required check that has never reported blocks every PR, so `Label gate` and `PR title` must be on the default branch before the ruleset requires them. Both run on `pull_request_target`, which uses the default branch's copy, so a PR can't pass them by editing the workflow, and the PR that adds them doesn't run them.

## Steps

1. **Inputs.** Get the repository (`OWNER/NAME`) and its CI check from the latest PR's check runs:
   `gh api repos/OWNER/NAME/commits/<head sha>/check-runs --jq '.check_runs[] | [.name, .app.id] | @tsv'`.
   Xcode Cloud reports as app 117084 with names like `Contadino | PR - Fast Gate`; pick the fast PR gate. Done when you have the exact check name and app id.
2. **Audit workflows.** The new Actions policy fails any step that uses a third-party action or a tag instead of a full commit SHA. List every `uses:` under `.github/workflows/` on the default branch; each must be `actions/*` or `github/*` pinned to a 40-character SHA. Fix the rest in the workflows PR (step 4). Done when every `uses:` passes or has a fix in that PR.
3. **Settings.** Run `scripts/apply-github-setup.sh settings --repo OWNER/NAME --dry-run`, show the maintainer the output, and apply without `--dry-run` once they agree. This sets the merge options, Wiki and Projects off, the Actions policy, the read-only workflow token and the `needs-human-verification` label. Workflows that step 2 flagged fail from here until the workflows PR merges; when one of them is a required check, merge that PR before applying.
4. **Workflows PR.** On a branch in the repository, add:
   - [`assets/workflows/pr-label-gate.yml`](assets/workflows/pr-label-gate.yml) and [`assets/workflows/pr-title.yml`](assets/workflows/pr-title.yml) under `.github/workflows/`
   - [`assets/dependabot.yml`](assets/dependabot.yml) as `.github/dependabot.yml`, unless one exists: then add the `github-actions` entry to it
   - [`assets/agents-github-workflow.md`](assets/agents-github-workflow.md) in `AGENTS.md`, with `<CI check>` and the one-way-door list filled in for this repository, replacing any older PR or branch rules it repeats
   - the workflow fixes from step 2

   Open the PR with the `pull-request` skill. The maintainer merges it. Done when both workflow files are on the default branch.
5. **Ruleset.** Run `scripts/apply-github-setup.sh ruleset --repo OWNER/NAME --ci-check '<name>' [--ci-app-id <id>] --dry-run`, show it, then apply. It updates the ruleset that already targets the default branch, keeping rules it doesn't manage, or creates one.
6. **Verify.** `scripts/apply-github-setup.sh verify --repo OWNER/NAME --ci-check '<name>' [--ci-app-id <id>]`, with the same app id as step 5, prints `ok` for every line and exits 0.

Codex reviews come from the maintainer's Codex GitHub connector; ask them to enable it for the repository if it isn't. Auto-merge stays the maintainer's: this setup allows it, and agents leave it off.
