## GitHub workflow
- Write and open PRs with the `pull-request` skill (g0ld2k/Skills). PRs are squash-merged: the PR title becomes the commit subject on `main` and the PR body becomes its message.
- Titles are Conventional Commit subjects (`fix(history): hide row separators`); the required "PR title" check enforces the format.
- The `main` ruleset allows squash merges only, requires linear history, and requires the "<CI check>", "Label gate" and "PR title" checks. Branches don't need to be up to date with `main`; use `gh pr update-branch` when one needs the latest `main`.
- One-way doors: <this repo's list, e.g. persisted schema changes, data migrations, purchases>. Mark them one-way in Merge Danger and add the `needs-human-verification` label; the required "Label gate" check blocks merging until the maintainer removes it.
- Codex reviews every PR through its GitHub connector and again on each push until it approves. A PR is ready only when Codex reacts with 👍 on the PR body; address its review comments until it does.
- Agents never enable auto-merge. The maintainer reviews every PR and is the only one who enables auto-merge.
