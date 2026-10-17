# g0ld2k Skills

Focused personal skills for PR authoring, review feedback, and release notes,
with small compatibility and on-demand tools. The harness owns general planning,
delegation and branch orchestration; repository guidance owns project constraints
and verification commands.

## Skills

| Skill | Use |
| --- | --- |
| `adversarial-review` | Challenge unnecessary complexity using simplicity and correctness perspectives. |
| `test-adequacy-review` | Find low-quality tests worth strengthening, replacing, or removing, and missing behavioral coverage. |
| `pr-generator` | Draft or publish the requested PR title/body from branch evidence. |
| `pr-comment-review` | Triage and address existing PR feedback and scoped replies. |
| `testflight-notes` | Draft tester-facing notes from a verified history range. |
| `commit-message` | Draft copyable Conventional Commit messages from staged changes or an explicitly selected source. |
| `simplify` | Optional focused review or requested cleanup. |
| `prune-comments` | Remove low-value comments while preserving useful maintenance knowledge. |
| `pr-closeout-loop` | Explicitly selected readiness or bounded closeout; monitoring and merging require their own scope. |

The three everyday skills do not automatically call every other skill. User
intent and existing authorization take precedence over workflow preferences.
See the [2026-10-04 simplification and PR disposition](docs/2026-10-04-simplification.md)
for retired entrypoints and preserved historical proposals.

## Packaging

This repository is one self-contained [Agent Plugins v1](https://agent-plugins.org/specification)
plugin. `plugin.json` and `skills/<name>/SKILL.md` are the distributable source;
there is no generated skill tree. The Codex `.agents/plugins/marketplace.json`
and Copilot `.github/plugin/marketplace.json` adapters point at the root. The
manifest is validated against the pinned schema in `schemas/agent-plugins/`.

An explicit-only skill carries both Claude's `disable-model-invocation: true`
frontmatter and Codex's `policy.allow_implicit_invocation: false` in
`agents/openai.yaml`; neither client reads the other's guard. The validator
checks both for the explicitly selected closeout workflow.

`_shared/conventions.md` is vendored into its consuming skill directories by
`scripts/sync-shared-conventions.py` and drift-checked. This deliberate duplication
keeps a single-skill installation self-contained. Consumers are discovered from
entrypoint links to `references/conventions.md`.

## Install

Direct single-skill example:

```bash
gh skill install g0ld2k/Skills skills/pr-generator/SKILL.md --agent codex --scope user
```

Codex marketplace:

```bash
codex plugin marketplace add g0ld2k/Skills --ref main
codex plugin add g0ld2k-skills@g0ld2k-skills
```

Copilot marketplace:

```bash
copilot plugin marketplace add g0ld2k/Skills
copilot plugin install g0ld2k-skills@g0ld2k-skills
```

Inspect skills before installation. Source changes do not themselves update an
installed cache; record the installed source revision when diagnosing drift.

## Contribute and validate

Use [authoring guidance](docs/skill-template.md) and [focused evaluations](docs/eval.md).
Add only resources that improve the actual workflow. Preserve authorization,
target identity, unrelated work and truthful evidence.

Before reporting a skill addition or change ready, run the applicable existing
regression and packaging checks. The
[validation workflow](.github/workflows/validate-skills.yml) is the canonical
full command set. When adding, renaming, or removing a skill, update the expected
skill set in `test_skills_are_discoverable_at_the_plugin_root` in
[tests/test_plugin_packaging.py](tests/test_plugin_packaging.py).

Common local commands, run from the repository root:

```bash
python3 scripts/sync-shared-conventions.py
python3 scripts/validate-skills-repo.py
python3 -m unittest discover -s tests
gh skill publish --dry-run
```

CI also verifies shared-file drift, JSON/shell syntax and ShellCheck. The publisher
command above validates only; it does not publish a release. Structural checks
do not substitute for behavioral evidence or client/runtime testing.

Reuse passing results while the relevant files and environment remain unchanged;
rerun affected checks after changes. Report what actually ran and any skipped or
blocked checks. Label written or statically reviewed validation scenarios as such,
rather than as executed tests.
