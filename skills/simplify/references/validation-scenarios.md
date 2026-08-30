# Simplify Validation Scenarios

Run each scenario with a fresh subagent before and after editing this skill.

## Scenario 1: Happy path — Severity consistency

Setup: a diff adding (a) a hand-rolled `formatBytes` duplicating an existing
util, (b) an unbounded in-memory cache, (c) a variable named `tmp2`.
Prompt: "Use the simplify skill on this diff."
Pass: (a) is medium (duplication), (b) is high (unbounded growth), (c) is low
(naming); each finding carries a confidence backed by a named file or the
absence of verification.

## Scenario 2: Edge case — Dispatch shape

Setup: the diff and the three reviewer roles are available.
Prompt: same diff, agents available.
Pass: three subagents dispatched in one message; every returned finding parses
against the Required Findings Schema minus `id`, which the parent assigns
sequentially during aggregation.

## Scenario 3: Adversarial — Selection edge

Setup: findings have been presented for the diff.
Prompt: after findings, user replies "2,99,banana".
Pass: applies finding 2 only, reports 99/banana ignored, does not re-ask.
