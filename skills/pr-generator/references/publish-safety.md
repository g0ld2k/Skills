# Publish Safety

Read this reference only after Step 4 approves the publish fingerprint and
before the first remote mutation.

## Verify the inventoried identity

The approved fingerprint already contains separate target/base and head/push
identities. Re-derive them from the same sources before mutation. A push remote's
effective URL must map to the inventoried PR head repository, while the base
OID comes from the target repository URL.

```bash
gh pr list --repo "$target_repo" --head "$branch" --state open \
  --json number,url,title,body,baseRefName,headRefOid,headRepositoryOwner
git ls-remote "$target_url" "refs/heads/$base_branch"
git ls-remote "$push_url" "refs/heads/$push_branch"
```

An empty `gh pr list` result is the documented no-open-PR state; a command
error is a lookup failure.

For create, re-derive the approved selector from the effective push URL: a bare
branch for the target repository; `user:branch` only for a verified user-owned
fork. An organization-owned cross-repository head needs an API/MCP operation
that supports it explicitly or blocks.

A lookup error blocks. An absent candidate head for an approved create remains
a valid observed state only when the fingerprint recorded that absence.

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

   ```bash
   gh pr edit "$pr_number" --repo "$target_repo" \
     --title "$title" --body-file "$pr_body_file"
   gh pr create --repo "$target_repo" --base "$base_branch" --head "$head_selector" \
     --title "$title" --body-file "$pr_body_file"
   ```

The MCP path performs the equivalent observations and mutations in the same
order. Any invalidation returns to inventory and requires a newly displayed
fingerprint and approval; never reinterpret create authority as update
authority or vice versa.
