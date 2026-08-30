# g0ld2k skills

Reusable Agent Skills for commit messages, pull requests, review closeout,
release notes, and work orchestration.

## Skill Catalog

| Skill | Purpose |
| --- | --- |
| `catch-me-up` | Build a mental model of unfamiliar code, architecture, or history via evidence-backed exploration. |
| `commit-message` | Draft evidence-based Conventional Commit messages from staged changes. |
| `integration-branch-orchestrator` | Plan autonomous PR work through integration branches and human promotion gates. |
| `pr-closeout-loop` | Close out existing PRs through review feedback, CI, approval, and merge readiness. |
| `pr-comment-review` | Triage, fix, and reply to unresolved pull request review feedback. |
| `pr-generator` | Draft, create, or update GitHub pull requests after explicit approval. |
| `simplify` | Review changed code for reuse, quality, and efficiency issues. |
| `testflight-notes` | Draft tester-facing TestFlight or release notes from git history. |
| `work-request-orchestration` | Turn issues, milestones, epics, and plans into validated branch-to-PR workflows. |

## Repository Shape

- `skills/<skill-name>/SKILL.md` contains the canonical skill instructions.
- `skills/<skill-name>/references/` contains optional supporting notes.
- `skills/<skill-name>/scripts/` contains optional helper scripts used by the skill.
- `skills/<skill-name>/agents/openai.yaml` contains Codex/OpenAI UI metadata.
- `packaging/<plugin-name>.json` defines one portable plugin and its member skills.
- `plugins/<plugin-name>/` contains generated Agent Plugins v1 packaging: `plugin.json` and the fixed `skills/` directory.
- `.agents/plugins/marketplace.json` and `.github/plugin/marketplace.json` are thin Codex and GitHub Copilot adapters that point to the same package directories.
- `schemas/agent-plugins/1.0.0/plugin.schema.json` is the pinned Agent Plugins v1 manifest schema used by the validator.

## Add a New Skill

1. Use `docs/skill-template.md` as the blueprint, not a literal copy: create
   `skills/<name>/SKILL.md` starting from the template's frontmatter block
   (filled in), then write each section the template prescribes (its quoted
   `## …` headings become your real headings). No template prose survives into
   the finished skill — delete the `DOCS-ONLY` blocks, the `## Frontmatter`
   rules section, and every guidance line as you replace it.
2. Create `skills/<name>/agents/openai.yaml` from the template's stub.
3. Create `skills/<name>/references/validation-scenarios.md` with at least 3
   scenarios (happy path, edge case, adversarial) — the template's Validation
   Scenarios section points at it.
4. Add the skill to exactly one `packaging/<plugin-name>.json` `skills` array.
   Add it to that config's `shared_conventions_consumers` array too if the
   skill keeps the template's `references/conventions.md` link.
5. Add a row for the skill to the `## Skill Catalog` table above.
6. Run the sync + generate + validate commands:

```bash
python3 scripts/sync-shared-conventions.py
python3 scripts/generate-plugin-packages.py
python3 scripts/validate-skills-repo.py
```

Agent Plugins v1 discovers skills from immediate `skills/<name>/SKILL.md`
directories. The portable `plugin.json` cannot list or relocate skills. Keep
client-specific behavior in that client's metadata; for example,
`agents/openai.yaml` sets `policy.allow_implicit_invocation: false` for
explicit-only skills. `disable-model-invocation` is not a portable Agent
Skills field and must not appear in `SKILL.md` frontmatter.

## Direct Agent Skills Install

Install a canonical skill directly from the repository with `gh skill`:

```bash
gh skill install g0ld2k/Skills skills/commit-message/SKILL.md --agent codex --scope user
gh skill install g0ld2k/Skills skills/pr-generator/SKILL.md --agent claude-code --scope user
gh skill install g0ld2k/Skills skills/pr-comment-review/SKILL.md --agent github-copilot --scope project
```

Use exact `skills/<skill-name>/SKILL.md` paths for direct installs so `gh skill`
does not also install a generated plugin bundle under `plugins/`.

Validate the direct publisher shape:

```bash
gh skill publish --dry-run
```

## Marketplace Install Examples

Codex:

```bash
codex plugin marketplace add g0ld2k/Skills --ref main
codex plugin add g0ld2k-skills@g0ld2k-skills
```

GitHub Copilot CLI:

```bash
copilot plugin marketplace add g0ld2k/Skills
copilot plugin install g0ld2k-skills@g0ld2k-skills
```

## Validation

Run the same structural checks used by CI:

```bash
python3 scripts/generate-plugin-packages.py
git diff --exit-code
status="$(git status --porcelain)"
if [ -n "$status" ]; then echo "$status"; exit 1; fi
python3 scripts/validate-skills-repo.py
find plugins .agents .github schemas -name '*.json' -print |
  while IFS= read -r file; do python3 -m json.tool "$file" >/dev/null; done
find skills plugins scripts -type f -name '*.sh' -print |
  while IFS= read -r file; do bash -n "$file"; done
gh skill publish --dry-run
```

CI validates repository structure, generated packaging freshness, the pinned
Agent Plugins v1 manifest schema, JSON syntax, shell script syntax, and the
`gh skill` publisher shape. It does not run client runtime validation or skill
evals.

Optional local checks:

```bash
scripts/smoke-test-marketplaces.sh
```

The smoke test uses temporary Codex and Copilot homes, adds this repository as
a local marketplace, browses the catalog, and installs `g0ld2k-skills` through
both adapters. It requires both the `codex` and `copilot` CLIs.

## Security

Skills can influence agent behavior and may guide state-changing actions such
as commits, pull request updates, comments, or merges. Inspect third-party
skills before installing them, and keep explicit approval gates for write
operations.
