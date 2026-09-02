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

1. Split by whole file first, in scope-index order. Fallback content splits by
   whole line-numbered file the same way.
2. If one file is still too large, split that file by hunk, keeping each hunk
   intact with the context lines Git already attached to it. Hunk boundaries
   carry their own context, so partitions do not overlap.
3. If a single hunk is still too large, block and name its location; never
   truncate content.

Give each partition a stable identifier (`path`, or `path#hunkN`). Every
request still carries the complete scope index so reviewers can see the rest
of the change and keep findings anchored to their own partition.

## Coverage

Dispatch all three roles (reuse, quality, efficiency) for every partition, and
wait for the whole matrix before aggregating. A role/partition pair that
fails, is missing, or again reports it could not read its assignment blocks;
do not present findings from the pairs that succeeded as a complete review.
Then return to SKILL.md step 3: deduplicate across partitions before assigning
IDs, since one abstraction or duplicate may surface in several partitions.
