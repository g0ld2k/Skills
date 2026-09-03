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
coverage, checks each target, and writes canonical preview JSON that embeds the
root and all replies for each active thread. Present the artifact and printed
`sha256:...` digest for approval. Approval must name that digest and cover
posting all represented replies.

After approval, do not edit the replies, target, preview, or digest. Post with:

```bash
bash "$skill_dir/scripts/post_pr_replies.sh" \
  --owner <owner> --repo <repo> --pr <number> \
  --replies-file <replies.json> \
  --preview-file <preview.json> \
  --approved-digest <sha256:...>
```

The helper first snapshots the supplied preview into its private work directory,
then hashes, validates, and reads only that snapshot. It refreshes the complete
inventory before each mutation. Root edits, new replies, changed mappings, or
added unresolved threads invalidate the approved thread state. A newly resolved
thread is a reported skip. Any other drift, lookup failure, or malformed
response aborts the remaining batch and reports prior mutations; rebuild the
preview and obtain fresh approval.

Reply bodies are sent as JSON input files, never command-line fields.

## MCP Equivalent

Fetch every outer thread page and nested comment page. Reject API errors,
missing targets, malformed nodes, and incomplete cursors. Construct the same
canonical preview, including full thread state, and present its exact text for
approval; without a digest helper, approval binds to those bytes. After exact
approval, compare target, reply, root, and reply-history state byte for byte,
then verify repository, PR, root, and unresolved state immediately before each
reply. Abort all later replies on any uncertain check.
