# Reviewer Protocol

Use this protocol for every resolved simplify scope.

## Requests and partitioning

The maximum rendered reviewer request is 48,000 UTF-8 bytes. Count the role
instructions, complete compact scope index, partition identifier, and assigned
content exactly as sent. If fixed instructions plus the index exceed the
budget, block and request a narrower scope.

Partition changed patches by whole file, then related hunks, then coherent
changed-line ranges. Partition fallback content by whole line-numbered file,
then coherent ranges. Use at most 20 unchanged context lines of overlap. Shrink
ranges or overlap until each rendered request fits; never truncate content or
omit the complete index. Block on an indivisible oversized unit and name its
location.

Each partition receives three read-only passes:

- **Reuse:** locate existing utilities or abstractions that replace duplicate
  functions or hand-written inline helpers.
- **Quality:** inspect redundant state, parameter sprawl, near-duplicates,
  leaky abstractions, stringly typed code, and unnecessary nesting.
- **Efficiency:** inspect repeated work or I/O, missed safe concurrency,
  hot-path blocking, TOCTOU pre-checks, resource growth/leaks, and overly broad
  operations.

Each request includes its role criteria, the schema and enum definitions below,
the complete scope index, and assigned content. It instructs the reviewer to
make no edits and return only the JSON array.
Reviewers may inspect repository context read-only, but findings stay anchored
to assigned changed locations.

## Finding schema

Reviewers return a JSON array without IDs. Every item contains:

| Field | Rule |
| --- | --- |
| `category` | Reviewer role: `reuse`, `quality`, or `efficiency` |
| `severity` | `high`, `medium`, or `low` |
| `confidence` | `high`, `medium`, or `low` |
| `location` | `path:line` inside assigned changed scope |
| `observed_evidence` | Concrete symbol, operation, or behavior at that location |
| `summary` | One-sentence problem |
| `proposed_fix` | One-sentence remedy |
| `existing_abstraction` | Located utility/abstraction for reuse; otherwise `null` |
| `existing_abstraction_location` | Its repository `path:line` for reuse; otherwise `null` |

Severity is `high` for introduced correctness/security risk, unbounded resource
growth, or measurable hot-path regression; `medium` for verified duplication,
leaky abstraction, or compounding redundant work; `low` for naming, style, or
optional behavior-neutral cleanup.

Confidence is `high` when the alternative, duplicate, or hot path is located;
`medium` when evidence is concrete but the alternative is unverified; and
`low` for a heuristic concern.

## Evidence gate

Wait for every dispatched result and parse each JSON array. Reject missing
fields, invalid enums, out-of-scope locations, vague evidence, and reuse items
without both abstraction fields. When concrete evidence supports the finding
but not its confidence, downgrade confidence to `low`; never upgrade it.
Deduplicate overlapping findings, keep the clearest evidence-backed item, and
assign IDs only after this gate. Report rejection counts and reasons.
