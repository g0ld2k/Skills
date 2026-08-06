# g0ld2k Skills

Reusable Agent Skills for commit messages, pull requests, review closeout,
release notes, and work orchestration.

## Skill Catalog

| Skill | Purpose |
| --- | --- |
| `apple-accessibility-review` | Audit Apple platform app accessibility with user-impact-ranked, evidence-backed findings. |
| `apple-design-advisor` | Evidence-graded design guidance, implementation direction, and best practices for Apple platforms. |
| `apple-ui-review` | Audit built UI against Apple platform conventions with severity-ranked findings. |
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
- `_shared/` holds single-source reference material vendored into consumer
  skills by `scripts/sync-shared-conventions.py`: `conventions.md` plus the
  named `shared_reference_groups` in `packaging/g0ld2k-skills.json` (e.g. the
  `apple` group backing the Apple design suite — see
  `docs/apple-design-advisor-architecture.md`).
- `plugins/g0ld2k-skills/` is generated packaging for Claude, Codex, and GitHub Copilot.
- `.claude-plugin/`, `.agents/plugins/`, and `.github/plugin/` expose marketplace metadata.

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
4. Add the skill to `packaging/g0ld2k-skills.json`: the `skills` array, and
   the `shared_conventions_consumers` array too if the skill keeps the
   template's `references/conventions.md` link. If the skill consumes a
   shared reference group (like the Apple suite's `_shared/apple/` corpus),
   add it to that group's `consumers` list as well.
5. Add a row for the skill to the `## Skill Catalog` table above.
6. Run the sync + generate + validate commands:

```bash
python3 scripts/sync-shared-conventions.py
python3 scripts/generate-plugin-packages.py
python3 scripts/validate-skills-repo.py
```

## Direct Agent Skills Install

Install a canonical skill directly from the repository with `gh skill`:

```bash
gh skill install g0ld2k/Skills skills/commit-message/SKILL.md --agent codex --scope user
gh skill install g0ld2k/Skills skills/pr-generator/SKILL.md --agent claude-code --scope user
gh skill install g0ld2k/Skills skills/pr-comment-review/SKILL.md --agent github-copilot --scope project
```

Use exact `skills/<skill-name>/SKILL.md` paths for direct installs so `gh skill`
does not also install the generated plugin bundle under
`plugins/g0ld2k-skills/skills/`.

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

Claude Code:

```text
/plugin marketplace add g0ld2k/Skills
/plugin install g0ld2k-skills@g0ld2k-skills
```

## Validation

Run the same structural checks used by CI:

```bash
python3 scripts/generate-plugin-packages.py
git diff --exit-code
status="$(git status --porcelain)"
if [ -n "$status" ]; then echo "$status"; exit 1; fi
python3 scripts/validate-skills-repo.py
find plugins .claude-plugin .agents .github -name '*.json' -print |
  while IFS= read -r file; do python3 -m json.tool "$file" >/dev/null; done
find skills plugins scripts -type f -name '*.sh' -print |
  while IFS= read -r file; do bash -n "$file"; done
gh skill publish --dry-run
```

CI validates repository structure, generated packaging freshness, JSON syntax,
shell script syntax, and the `gh skill` publisher shape. It does not run Claude
runtime validation or skill evals.

Optional local checks:

```bash
claude plugin validate . --strict
copilot plugin install ./plugins/g0ld2k-skills
codex plugin marketplace add ./.
codex plugin add g0ld2k-skills@g0ld2k-skills
```

## Security

Skills can influence agent behavior and may guide state-changing actions such
as commits, pull request updates, comments, or merges. Inspect third-party
skills before installing them, and keep explicit approval gates for write
operations.
