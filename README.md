# g0ld2k Skills

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

This repository is one self-contained plugin described by the
[Agent Plugins v1 specification](https://agent-plugins.org/specification).

- `plugin.json` is the Agent Plugins v1 manifest for this repository.
- `skills/<skill-name>/SKILL.md` contains the canonical skill instructions and
  is discovered directly by plugin clients.
- `skills/<skill-name>/references/` contains optional supporting notes.
- `skills/<skill-name>/scripts/` contains optional helper scripts used by the skill.
- `skills/<skill-name>/agents/openai.yaml` contains Codex/OpenAI UI metadata.
- `.agents/plugins/marketplace.json` and `.github/plugin/marketplace.json` are
  thin Codex and GitHub Copilot adapters that point at the repository root.
- `schemas/agent-plugins/1.0.0/plugin.schema.json` is the pinned Agent Plugins v1
  manifest schema used by the validator.

Agent Plugins v1 discovers skills from immediate `skills/<name>/SKILL.md`
directories; there is no recursive search and the portable `plugin.json` cannot
list or relocate them. There is no generated copy of `skills/`: the root
manifest and the canonical skill tree are the distributable artifact.

The manifest schema sets `additionalProperties: false`, so `extensions` — keyed
by reverse-domain namespace — is the only legal home for future plugin-level
client-specific data.

Per-skill client behavior lives in that client's own metadata, and an
explicit-only skill needs a guard for **each** install path because neither
client reads the other's:

| Client | Guard | Location |
| --- | --- | --- |
| Claude Code | `disable-model-invocation: true` | `SKILL.md` frontmatter |
| Codex | `policy.allow_implicit_invocation: false` | `agents/openai.yaml` |

The validator requires both for every skill in `EXPLICIT_ONLY_SKILLS`, and
forbids the Claude field on every other skill. `disable-model-invocation` is a
Claude Code extension rather than a portable Agent Skills field; it is carried
deliberately so `gh skill install … --agent claude-code` cannot leave a
state-changing orchestrator implicitly invocable.

### Why `references/conventions.md` is vendored per skill

`_shared/conventions.md` is the single source of truth, copied into each
consuming skill by `scripts/sync-shared-conventions.py` and drift-checked in CI.
The duplication is deliberate: it keeps a single-skill
`gh skill install … skills/<name>/SKILL.md` self-contained, since that installs
one skill directory rather than the whole plugin. The sync script discovers
consumers from the skills that reference `references/conventions.md`, so adding
or removing that link is all it takes to opt in or out.

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
4. Add a row for the skill to the `## Skill Catalog` table above.
5. Run the sync and validation commands:

```bash
python3 scripts/sync-shared-conventions.py
python3 scripts/validate-skills-repo.py
```

## Direct Agent Skills Install

Install a canonical skill directly from the repository with `gh skill`:

```bash
gh skill install g0ld2k/Skills skills/commit-message/SKILL.md --agent codex --scope user
gh skill install g0ld2k/Skills skills/pr-generator/SKILL.md --agent claude-code --scope user
gh skill install g0ld2k/Skills skills/pr-comment-review/SKILL.md --agent github-copilot --scope project
```

Use exact `skills/<skill-name>/SKILL.md` paths to install one skill instead of
the complete plugin.

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
python3 scripts/validate-skills-repo.py
python3 scripts/sync-shared-conventions.py
git diff --exit-code
status="$(git status --porcelain)"
if [ -n "$status" ]; then echo "$status"; exit 1; fi
python3 -m unittest discover -s tests
find plugin.json .agents .github schemas -name '*.json' -print |
  while IFS= read -r file; do python3 -m json.tool "$file" >/dev/null; done
find skills scripts -type f -name '*.sh' -print |
  while IFS= read -r file; do bash -n "$file"; done
gh skill publish --dry-run
```

The validator checks the Agent Plugins v1 manifest against the pinned schema,
skill frontmatter and naming, `agents/openai.yaml` metadata, cross-skill
references, local links, and shared-conventions freshness. CI additionally
checks JSON syntax, shell script syntax, and the `gh skill` publisher shape. It
does not run client runtime validation or skill evals.

Optional local checks:

```bash
codex plugin marketplace add ./.
codex plugin add g0ld2k-skills@g0ld2k-skills
```

## Security

Skills can influence agent behavior and may guide state-changing actions such
as commits, pull request updates, comments, or merges. Inspect third-party
skills before installing them, and keep explicit approval gates for write
operations.
