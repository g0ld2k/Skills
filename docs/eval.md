# Evaluating skill changes

Use representative requests and meaningful safety boundaries. Structural checks
verify packaging and links; they do not prove good decisions. Simulated tool calls
do not prove live client behavior or external side effects.

For a behavioral change, define what a reviewer should be able to observe in
the result. Compare baseline and candidate against those criteria on the same
bounded request and artifacts. Include direct and indirect triggers, an adjacent
request that should not activate, and the relevant edge cases. Record where
each version meets or misses the criteria, including when both pass.

For complex or consequential behavior, use an independent evaluator with the
request, skill, and minimum raw artifacts. Do not tell it the intended answer or
prior finding. Record the exact model/reasoning setting when available, client,
skill revision and what was actually exercised. Use the current target model;
secondary-model/client coverage is useful when changed contracts require it,
not a mandatory full matrix for every edit. State unavailable coverage honestly.

Use disposable local repositories for Git scenarios (the existing
`scripts/make-fixture-repo.sh` provides one). Mock external writes: evaluations
must not post, push, resolve, merge, or operate on credentials. Keep raw evaluation
artifacts outside the working tree and put a concise result in the PR.

Observe successful completion, preserved user scope/authority, meaningful evidence,
and whether missing capabilities block only the dependent operation. Check known
boundaries such as draft-only work, unrelated changes, stale remote state, failed
validation and ambiguous feedback. Observe duplicate approval requests and
unnecessary workflow transitions directly; do not infer token/time savings from
word counts or agent counts.

Run required repository checks and tests relevant to changed executable behavior.
Reuse unchanged successful verification; repeat or broaden for edits, failures,
or unresolved concerns. Formatting-only changes need structural checks rather
than a fresh model evaluation. Use per-skill scenarios as examples, not an exact
prose or tool-count contract.

See the [skill guidance](https://learn.chatgpt.com/docs/build-skills) and
[GPT-6.2 prompting guidance](https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra).
