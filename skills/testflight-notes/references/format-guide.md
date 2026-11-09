# TestFlight Build Notes Format Guide

## Copy-ready output

Return each complete version in its own fenced `text` block. The fence provides a copy button; its contents are plain text ready for TestFlight or App Store Connect.

When producing separate platform versions, place the platform name (for example, iOS, macOS, or visionOS) outside and immediately before its block. A shared version needs only one block. Each platform block stands alone, including its shared changes; avoid references to another version.

Inside each block:
- Start with `What's new in this build:`.
- Follow with an optional release-context paragraph, then the sections.
- Use standalone uppercase headers `NEW`, `IMPROVED`, and `FIX`, in that order, omitting empty sections.
- Place each entry under its section as a `•` bullet. The section header supplies the category; bullets contain only the change description.
- Separate the introduction and each section with a blank line. Keep bullets within a section on consecutive lines.
- Use plain text without Markdown headings or emphasis, and end after the last bullet without a trailing blank line.

Keep platform labels, evidence caveats, citations, and explanatory commentary outside the blocks.

## Release context

Include an RC, version, or release-stage blurb only when the user requests or supplies that context. Use the supplied version and stage; keep the skill reusable across releases. An RC blurb may invite final checks of relevant workflows without implying validation that has not occurred.

## Entry wording

Write one or two short, tester-facing sentences per bullet. Lead with observable outcomes, such as “Editing a session preserves your scroll position.” Keep platform scope explicit within a bullet when needed for companion features such as Apple Watch.

## Length budget

Measure each block's contents independently, including its opening line, optional blurb, headers, bullets, spaces, and newlines. The hard limit is 4,000 characters per block; target at most 3,800. Fence delimiters and external platform labels do not count.

If a block exceeds the budget, shorten secondary details, merge related improvements, then drop the lowest-impact improvements. Preserve high-impact fixes wherever possible.

## Example structure

The placeholders below illustrate the format; replace them with evidence-supported changes. For separate versions, put the appropriate platform name before each fence.

```text
What's new in this build:

NEW
• <New capability and its benefit.>

IMPROVED
• <Improvement to an existing workflow.>

FIX
• <Previously incorrect behavior that is corrected.>
```

## No user-facing changes

If no supported user-visible changes remain, say so plainly outside a copyable
block. Report unreadable evidence as a gap. Neither case supports an invented
quality or stability entry.
