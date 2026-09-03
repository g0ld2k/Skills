# Oversized Scope Protocol

Read this only when a resolved simplify scope cannot be reviewed in one
request per role: either the indexed scope is plainly too large to send whole,
or a reviewer reports it could not read its whole assignment, or returns a
truncated or unparseable result. Small scopes never come here.

## Why observation, not a byte limit

An agent cannot reliably count rendered bytes, and reviewer capacity differs
by client. The trigger is therefore observable: a reviewer that cannot read
its whole assignment says so, and the parent partitions and re-dispatches.

## Partitioning

1. Split by whole file first, in scope-index order.
2. Split an oversized fallback file into stable, adjacent, non-overlapping
   line ranges and retain its original line numbers.
3. Split an oversized Git-patch file by hunk, keeping each hunk intact with
   Git's context lines; partitions do not overlap.
4. If one hunk or minimum useful line range is still too large, block and name
   it; never truncate content.

Give each partition a stable identifier (`path`, `path#hunkN`, or
`path#L<start>-L<end>`). Every request carries the complete scope index and
keeps findings anchored to its partition.

## Coverage

Dispatch all three roles (reuse, quality, efficiency) for every partition, and
wait for the whole matrix before aggregating. A role/partition pair that
fails, is missing, or again reports it could not read its assignment blocks;
do not present findings from the pairs that succeeded as a complete review.
Then return to SKILL.md step 3: deduplicate across partitions before assigning
IDs, since one abstraction or duplicate may surface in several partitions.
