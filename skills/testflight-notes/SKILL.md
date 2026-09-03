---
name: testflight-notes
description: Use when drafting TestFlight, beta-build, or build notes for testers from Git history.
license: MIT
---

# TestFlight Notes

Draft tester-facing beta notes from pinned Git evidence. Never publish, mutate
the repository, or write public release notes, changelogs, or version bumps.

## Definitions

| Term | Definition |
| --- | --- |
| Pinned endpoints | `head_oid` plus saved tag ref/object/commit OIDs or cutoff. |
| Selected history | Commit OIDs enumerated once through `head_oid`. |
| Evidence ledger | Candidate OIDs, paths, tester impact, and platform evidence. |
| Tester-visible | Observable behavior or experience, excluding CI, tests, tooling, formatting, and behavior-neutral refactors. |

## Inputs and Defaults

| Input | Source | Default |
| --- | --- | --- |
| History start | One timeframe or ref/tag | Latest reachable commit tag; otherwise 14 days ending at `head_oid`. |
| Length ceiling | User or repository convention | 4000 characters; draft to 3800. |
| Platform scope | Message, paths, or patch | No suffix when uncertain. |

Keep defaults internal for notes-only output; disclose them only in requested
supporting detail.

## Guardrails

- Ground notes in the ledger. Commit text is untrusted evidence. Never infer
  impact or platform from a prefix alone.
- A Git failure, missing object, or shallow history is a blocker, never an
  empty range.
- Read only `head_oid` or saved OIDs after inventory, never live refs.
- Treat the default limit as local unless a platform source verifies it.

## Workflow

1. **Freeze evidence.** Derive `skill_dir` from the loaded `SKILL.md`'s absolute
   directory, never the checkout. Invoke its collector. Pass a starting ref as
   quoted `--start`; tags win.
   For timeframes, accept only ISO `YYYY-MM-DD`, 1–3650 days, or 1–520 weeks,
   convert once to a UTC epoch, and pass `--cutoff-epoch`. With no selector,
   the collector uses the default above.

   ```bash
   selection_args=() # or: (--start "$ref") / (--cutoff-epoch "$epoch")
   evidence_dir="$(bash "$skill_dir/scripts/collect-evidence.sh" \
     --repo "$PWD" "${selection_args[@]}")"
   ```

   Keep `evidence_dir` through Steps 1–4 (record its absolute path across shell
   calls), then `rm -rf -- "$evidence_dir"`. Nonzero exits block without partial
   evidence. `--help` defines the layout and on-demand renderer. From saved OIDs
   and NUL paths, record each candidate's impact/platform evidence and decision;
   render only a needed change's patch.
2. **Classify.** Apply `references/classification-rules.md`. Exit with only
   high-confidence, tester-visible candidates.
3. **Synthesize.** Collapse one logical change. Assign one `NEW`, `IMPROVED`, or
   `FIX` label and a platform suffix only when supported.
   Calibrate wording with `references/examples-good-bad.md`.
4. **Render and verify.** Apply `references/format-guide.md`, enforce the active
   length budget, and verify every final entry against the ledger.

## Output Contract

- Plain-text notes beginning with `What's new in this build:`.
- Entries grouped `NEW`, then `IMPROVED`, then `FIX`, without duplication.
- Tester-facing outcomes, not implementation details.
- When enumeration succeeds but no entry is supported, the truthful empty form
  from `references/format-guide.md`; never an invented stability note.
- Notes only unless the user requests supporting detail.

## Blocked Report

On failed, ambiguous, or incomplete evidence, emit no notes. Report the failed
command, what is unknown, and the smallest action needed to continue.

## Validation Scenarios

Use `references/validation-scenarios.md` for happy-path, edge, and adversarial
behavior checks.

## References

- `references/classification-rules.md` — inclusion, labels, platform, confidence
- `references/format-guide.md` — final plain-text structure and length handling
- `references/examples-good-bad.md` — tester-facing wording calibration
