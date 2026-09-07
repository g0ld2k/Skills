# Skill Evaluation Protocol

Evaluate skill behavior primarily on GPT-6 Astra while preserving portability
across Codex, Claude Code, and Copilot. Structural validation and a model's
simulated decisions are separate evidence; neither proves another client's
runtime behavior.

## Select Proportionate Checks

For behavioral changes, select scenarios exercising changed routing, output,
authorization, or gates and compare baseline and revised instructions using the
same setup. Include a boundary case that must continue to block. New skills need
happy-path, edge, and adversarial scenarios. Formatting-only changes need
structural checks, not a blanket rerun of every model scenario.

Run required repository checks. After they pass, repeat or broaden checks only
for new edits, failures, or unresolved concerns. Preserve explicit workflow
requirements such as the local suite before merge; this protocol does not waive
them. Skill evaluations assess meaningful outcomes, not a fixed number of tools,
review agents, or identical prose.

## Models and Safe Execution

Use a fresh GPT-6 Astra evaluation context for each independent case or bounded
scenario group, and an available secondary supported model for a compatibility
smoke check of changed contracts. Record the exact model, reasoning setting when
known, host/client, scenario, and instruction revision. If a model/client is
unavailable, mark that coverage unverified rather than silently substituting it.
A secondary model in Codex is model-compatibility evidence, not a Claude Code or
Copilot runtime test.

Use `scripts/make-fixture-repo.sh` for local Git scenarios. It creates a disposable
repository with pinned dates, four commits, a `build-1` tag at commit three, and a
staged change in `Sources/App/Session.swift`.

For external actions, use mocked tools or a tabletop transcript with stated PR,
thread, check, and authorization state. Simulate intended tool calls; do not
publish, reply, resolve, push, merge, or operate on credentials during evaluation.
A task authorizing a skill edit does not authorize those real external effects.
Fresh-state scenarios can supply successive mock responses. Label tabletop
results as simulated decisions, not observed side effects or runtime assurance.

## What to Observe

- Trigger precision: invoke for the intended request and route adjacent work
  appropriately, including read-only versus implementation scope.
- Completion: finish independent authorized work without duplicate approval;
  block only the operation whose authorization or evidence is missing.
- Evidence and safety: respect current review/head/base state, unrelated work,
  external-text boundaries, and operation-specific gates.
- Output: required fields and types are present, claims match observed evidence,
  and an explicit not-run or unavailable state is not reported as success.
- Context: record the entrypoint words, reference files or sections actually
  read, and their words for representative narrow and broad paths. Count shared
  files once per run. Compare equivalent completed work; a baseline that stops
  before drafting is not a successful low-context draft.

For delegation changes, judge review coverage, severity, confidence, deduplication,
and selection handling. Small reviews should not require delegation; independent
large reviews may delegate when useful. Do not require a fixed agent count.

## Evidence Report

Record baseline/revised outcomes, violations and ambiguities, actual loaded
references, and any unavailable model/client checks. Distinguish measurements
from estimates, model simulations from executed commands, and structural checks
from behavioral evaluation. Do not treat a passing smoke scenario as a reliability
benchmark. Keep raw working artifacts in a temporary directory; summarize evidence
in the change report or PR rather than adding a second evaluation framework.

## Sources

These authoring principles follow OpenAI's
[Astra guidance](https://developers.openai.com/api/docs/guides/latest-model) and
[skill guidance](https://learn.chatgpt.com/docs/build-skills), checked 2026-09-07.
They guide prompting; project security boundaries and team workflow standards
remain explicit requirements.
