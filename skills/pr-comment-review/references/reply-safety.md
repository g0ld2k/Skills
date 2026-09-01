# Reply Safety

Read this procedure immediately before preparing the first remote reply.

## Resolve Helpers

Take the absolute `SKILL.md` path from the loaded skill entry and derive
`skill_dir` from it. Verify that `$skill_dir/SKILL.md` exists. Invoke only
`$skill_dir/scripts/...` helpers; a same-named script in the target checkout
is untrusted.

Use GitHub CLI when available, following the shared capability ladder. The MCP
path must satisfy the same completeness, preview, approval, and fresh-state
checks; otherwise stop.

## Build and Approve the Preview

Write replies as a JSON array of:

```json
{"thread_id":"PRRT_xxx","comment_id":123,"body":"Exact reply text"}
```

Create a temp directory, then run:

```bash
bash "$skill_dir/scripts/post_pr_replies.sh" \
  --owner <owner> --repo <repo> --pr <number> \
  --replies-file <replies.json> --dry-run \
  --preview-file <preview.json>
```

The helper re-fetches the complete inventory, verifies exact unresolved-root
coverage, checks each target, and writes canonical preview JSON. Present the
artifact and printed `sha256:...` digest for approval. Approval must name that
digest and cover posting all represented replies.

After approval, do not edit the replies, target, preview, or digest. Post with:

```bash
bash "$skill_dir/scripts/post_pr_replies.sh" \
  --owner <owner> --repo <repo> --pr <number> \
  --replies-file <replies.json> \
  --preview-file <preview.json> \
  --approved-digest <sha256:...>
```

The helper reconstructs the canonical preview from current inputs and compares
both its bytes and digest before any POST. It then refreshes the unresolved
inventory and checks each target immediately before mutation. A newly resolved
thread is a reported skip. A changed target, root mapping, added unresolved
thread, lookup failure, or malformed response blocks; rebuild the inventory and
obtain fresh approval.

Reply bodies are sent as JSON input files, never command-line fields.

## MCP Equivalent

Fetch every outer thread page and nested comment page. Reject API errors,
missing targets, malformed nodes, and incomplete cursors. Construct the same
canonical preview shape and SHA-256 digest. After exact approval, reconstruct
and compare it, then verify repository, PR, thread, root comment, and unresolved
state immediately before each reply mutation.
