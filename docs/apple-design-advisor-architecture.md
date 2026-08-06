# Apple Platform Design Advisor — Architecture Proposal

Status: **Accepted** (implemented in this repository)

## Goal

Give coding agents the reasoning apparatus of an experienced Apple platform
engineer — not a mirror of the Human Interface Guidelines. The suite must:

- load only the knowledge the current task needs (progressive disclosure);
- treat the HIG as primary evidence while drawing on WWDC sessions, SF Symbols
  guidance, framework documentation, sample code, and App Review Guidelines;
- separate documented guidance, inferred convention, engineering
  recommendation, and subjective opinion — with confidence levels;
- support design guidance, implementation assistance, UI review, accessibility
  review, architecture discussion, and best-practice workflows;
- share reference material across skills without copy-drift;
- absorb new Apple frameworks and design-language shifts without rework.

## Approaches Considered

### A. One monolithic skill

A single `apple-design-advisor` skill whose SKILL.md routes every workflow and
whose `references/` tree holds all knowledge.

- Pros: zero duplication; one install; trivial cross-workflow consistency.
- Cons: one triggering description must cover six workflows, which degrades
  invocation precision (a review request and a "which navigation pattern"
  question want different postures); SKILL.md grows past the ~500-line
  progressive-disclosure budget or becomes a thin index that pushes every run
  through two levels of indirection; audit workflows (findings, severities)
  and advisory workflows (options, tradeoffs) have incompatible output
  contracts that would share one Output Contract section badly.

### B. Independent self-contained skills

One skill per workflow, each carrying its own copy of the evidence framework
and platform knowledge.

- Pros: perfect installability in isolation; precise triggering.
- Cons: the shared corpus (evidence taxonomy, platform matrix, domain index)
  is duplicated N ways with no drift control. The first HIG-era shift (e.g., a
  new design language) requires N hand-edits. This directly violates the
  maintainability requirement and this repo's own drift-checking philosophy.

### C. Hub skill + thin routers reading the hub at runtime

A knowledge-base skill holds the corpus; workflow skills reference the hub's
files by sibling path (`../apple-knowledge/references/…`).

- Pros: no duplication in git; precise triggering.
- Cons: sibling-path reads break the moment a skill is installed alone
  (`gh skill install` copies one directory), installed from the plugin bundle
  into a different layout, or run by an agent that sandboxes skill roots. The
  repo validator cannot even express "this link resolves outside the skill".
  Fragile in exactly the "canonical, widely installed" future the suite is
  meant for.

### D. Workflow skills + single-source vendored corpus (**recommended**)

A small set of workflow skills (advisory, UI review, accessibility review)
plus a single-source shared corpus in `_shared/apple/`, vendored into each
consumer skill's `references/apple/` by the repo's sync tooling and
freshness-checked by the validator — the same mechanism that already governs
`_shared/conventions.md`, generalized to named *shared reference groups*.

- Pros: edit-once maintenance with validator-enforced freshness; every
  installed skill is fully self-contained; per-workflow triggering precision
  and output contracts; the group mechanism is reusable by future suites
  (Android, web, …); adding a skill to the suite is one config entry plus a
  sync run.
- Cons: vendored copies exist in git (mitigated: generated-file headers and
  CI drift checks make them unmistakably derived); requires a one-time
  generalization of `sync-shared-conventions.py` and the validator.

## Decision

**Approach D.** It is the only option that simultaneously satisfies
installability-in-isolation, edit-once maintenance, and triggering precision,
and it composes with this repository's existing conventions instead of
inventing a parallel mechanism.

### Skill lineup (three skills covering six workflows)

| Skill | Workflows covered | Posture |
| --- | --- | --- |
| `apple-design-advisor` | design guidance, implementation assistance, architecture discussion, best-practice recommendations | Advisory: options, tradeoffs, recommendation |
| `apple-ui-review` | UI reviews | Audit: findings with severity + evidence |
| `apple-accessibility-review` | accessibility reviews | Audit: findings ranked by user impact |

Advisory workflows share one skill because they share a posture and output
contract (classified claims, confidence, reasoning, recommendation) and differ
only in emphasis — a mode table (house pattern, cf. `catch-me-up`) routes
between them. The two review workflows are separate skills because audits have
a distinct output contract (findings tables, severity ladders) and because
accessibility deserves first-class triggering ("audit VoiceOver support" must
not depend on the model generalizing from a UI-review description).

### Shared corpus `_shared/apple/`

| File | Contents | Why shared |
| --- | --- | --- |
| `evidence-framework.md` | Claim taxonomy (`[HIG]/[API]/[CONV]/[REC]/[OPINION]`), confidence levels, source hierarchy, verification and anti-fabrication rules | Every skill's claims are graded by it |
| `platform-conventions.md` | Per-platform idiom matrix: input model, navigation, layout metrics, window model, review emphasis | Every skill branches on target platform |
| `design-domains.md` | Domain index: key questions per domain + where authoritative guidance lives (HIG sections, WWDC themes, framework docs) | Every skill routes evidence-loading through it |

Workflow-specific material (advisory mode details, review checklists,
accessibility checklists, validation scenarios) stays per-skill in each
skill's own `references/`.

### Progressive disclosure (three levels)

1. **Metadata** — name + "Use when" description (always in context).
2. **SKILL.md body** — kept lean: mode/scope tables, workflow phases, output
   contract, and *routing instructions* naming which reference file to read
   for the task at hand.
3. **References** — shared corpus + workflow references, loaded selectively:
   the domain index tells the agent which domains the request touches; only
   those checklist sections and corpus entries are read.

### Evidence model

All three skills tag every substantive claim and grade its confidence
(defined in `evidence-framework.md`). The corpus deliberately stores
*pointers and reasoning*, not restated HIG text: which HIG section or WWDC
theme answers a question, what the stable convention is, and what must be
re-verified against current documentation (metrics, API availability,
design-language changes). Anti-fabrication rules (no invented WWDC session
numbers, no guessed point values stated as fact) are part of the shared
framework, not per-skill folklore.

### Extension recipe (long-term evolution)

- **New platform capability or framework** (e.g., a new design language, a new
  interaction model): add or amend rows in `_shared/apple/design-domains.md`
  and `platform-conventions.md`, run the sync script — every consumer updates
  atomically and CI fails if a copy drifts.
- **New workflow skill** (e.g., an App Store submission-readiness review):
  scaffold per `docs/skill-template.md`, add it to the `apple` group's
  `consumers` in `packaging/g0ld2k-skills.json`, sync, and write only its
  workflow-specific references.
- **New suite entirely**: declare another group under
  `shared_reference_groups` — the tooling is suite-agnostic.

### Tooling changes

- `packaging/g0ld2k-skills.json` gains `shared_reference_groups`:
  `{ "<group>": { "source": "_shared/<dir>", "consumers": [...] } }`.
  The legacy `shared_conventions_consumers` key is untouched.
- `scripts/sync-shared-conventions.py` also syncs every file of every group
  into `skills/<consumer>/references/<group>/` with a GENERATED header.
- `scripts/validate-skills-repo.py` drift-checks group copies exactly as it
  does `conventions.md`, including the "vendored but unlisted consumer" scan.
