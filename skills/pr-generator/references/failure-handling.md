# Publication failures

Report the failed operation and useful redacted evidence, retaining the draft.
Continue independent authorized work.

- Authentication or capability failure: use an already-authorized equivalent
  capability if available; otherwise state what access is missing.
- Lookup failure: do not reinterpret an error as an absent PR or branch.
- Rejected push: inspect the current remote and local relationship. Preserve
  unrelated commits; do not switch to force push or rebase merely to bypass the
  rejection. Reconcile within the user's authorized scope.
- Base mismatch: preserve the requested base; do not silently retarget.
- Uncertain create/update outcome: re-fetch the exact PR/branch before retrying
  so a timeout does not create duplicate or overwrite unexpected work.
- Failed validation: report the actual failure, continue authorized diagnosis,
  and satisfy repository policy before any action that depends on that check.
