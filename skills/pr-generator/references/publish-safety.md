# Publish Safety

Read this reference only after Step 4 approves the publish fingerprint and
before the first remote mutation.

## Resolve the publish identity

For an existing PR, use its actual head repository and ref. A push plan needs
a configured remote whose effective push URL maps to that repository; resolve
it with `git remote get-url --push <remote>`. Query the exact branch with
`git ls-remote`. Its OID must match the inventoried PR head OID before approval.

For a new PR, derive the head repository from the effective push URL, not the
remote name or fetch URL. Use a bare branch selector when that destination is
the target repository. For a cross-repository head, the owner-qualified form
`user:branch` is valid only after verifying a user-owned fork. An
organization-owned cross-repository head requires an API/MCP capability that
supports it explicitly; otherwise block.

Resolve the base branch on its target remote and verify its live OID. A lookup
error is a blocker, while an absent candidate head for a new PR is a valid
observed state.

## Revalidate and mutate

1. Fetch live repository, PR, base, and head-ref state. Rebuild the fingerprint
   from observations and the frozen title/body; do not regenerate the draft or
   rerun validation at this gate. G3 authorizes a push only when live `HEAD`
   still equals `approved_local_oid`; a moved local branch returns to inventory
   before any mutation. All other fingerprint inputs must also match.
2. When a push is approved, push the recorded commit rather than a moving
   branch name:

   ```bash
   git push "$push_remote" \
     "$approved_local_oid:refs/heads/$push_branch"
   ```

3. Fetch the exact branch, PR, and base again. G4 accepts only the planned
   branch/head transition from the recorded before OID (or absence) to
   `approved_local_oid`.
4. Rebuild all other fingerprint inputs. A new/disappeared PR, changed PR
   number or metadata input, base movement, unexpected head movement, changed
   selector, or changed title/body/validation evidence invalidates the plan.
5. For update, edit only the approved PR number after its head repository/ref
   and current metadata digest still match. For create, require the approved PR
   absence and base to remain current, then create with the approved selector.

The MCP path performs the equivalent observations and mutations in the same
order. Any invalidation returns to inventory and requires a newly displayed
fingerprint and approval; never reinterpret create authority as update
authority or vice versa.
