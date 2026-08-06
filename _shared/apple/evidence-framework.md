# Apple Evidence Framework

How every Apple-suite skill grades, cites, and verifies claims. Any
recommendation that could change what the user builds carries a claim tag and
a confidence level from this file.

## Claim Taxonomy

Tag every substantive claim with exactly one:

| Tag | Meaning | Example |
| --- | --- | --- |
| `[HIG]` | Documented Apple design guidance (Human Interface Guidelines or other official Apple design docs) | "Prefer standard navigation patterns; the HIG's Navigation and search section covers when to use tab bars vs. sidebars" |
| `[API]` | Framework documentation or API contract: availability, deprecation, documented behavior | "`NavigationView` is deprecated; `NavigationStack`/`NavigationSplitView` replace it" |
| `[CONV]` | Inferred platform convention: consistent across Apple's system apps and widely expected by users, but not explicitly written down | "Pull-to-refresh on a scrolled list is expected in content-feed apps on iOS" |
| `[REC]` | Implementation recommendation: engineering judgment grounded in `[HIG]`/`[API]`/`[CONV]` evidence | "Model this as `NavigationSplitView` now, even for iPhone-only launch, to keep the iPad/Mac path open" |
| `[OPINION]` | Subjective design taste: defensible, but a peer could reasonably disagree | "The denser card layout feels more at home next to Apple News than the airy one" |

Rules of use:

- `[HIG]` and `[API]` claims name their source specifically enough to look up:
  document plus section for guidance ("HIG > Layout"), symbol name for API.
- `[CONV]` claims name the corroborating observations (which system apps or
  system behaviors exhibit the convention).
- `[REC]` claims state the evidence they rest on and the tradeoff accepted.
- `[OPINION]` is allowed — experienced engineers have taste — but never
  disguised as one of the other four.

## Confidence Levels

| Level | Criteria |
| --- | --- |
| High | Directly documented and stable across recent OS releases, verified this session, or a convention corroborated by multiple system apps |
| Medium | Documented but possibly stale (annual HIG/OS churn), or a convention with limited corroboration |
| Low | Recalled without verification, version-dependent, contested, or extrapolated from adjacent guidance |

Confidence qualifies the *evidence*, not the writing: a Low-confidence claim
delivered decisively is a defect. Low-confidence claims that materially affect
the user's decision must either be verified (below) or explicitly flagged with
what would confirm them.

## Source Hierarchy

When sources conflict, prefer the higher row; within a row, prefer the more
recent statement:

1. Current Human Interface Guidelines (design questions) / current framework
   documentation (API questions)
2. App Review Guidelines — a hard constraint where it applies; design
   elegance never outranks rejection risk
3. WWDC sessions — strongest for rationale and "why", and often ahead of
   written docs in the months after WWDC
4. Apple sample code and framework release notes
5. Behavior of Apple's own system apps (the basis for `[CONV]` claims)
6. Established community convention — admissible only when Apple is silent,
   and always tagged `[CONV]` or `[OPINION]`, never `[HIG]`

## Verification and Currency

Apple revises the HIG and frameworks at least annually, and design-language
shifts (most recently the Liquid Glass material language introduced with the
OS 26 generation) can invalidate remembered guidance wholesale. Therefore:

- When web access is available and a claim is load-bearing, verify against
  developer.apple.com before presenting it, and mark it verified.
- When web access is not available, state the knowledge boundary rather than
  projecting past it: "as of my training data; confirm against the current
  HIG > Materials".
- Prefer guidance that has been stable across releases; call out anything
  known to churn (exact point values, material names, per-OS component
  availability).

## Anti-Fabrication Rules

These are the failure modes that most damage trust; treat them as hard stops.

- Never invent WWDC session numbers or titles. Cite a session only when
  confident of its actual title and year; otherwise point to the topic
  ("search WWDC sessions on adaptive layout").
- Never state exact metrics (point sizes, margins, minimum target sizes,
  contrast ratios) from shaky memory as fact. Either verify, or present the
  remembered value with its confidence and where to confirm it.
- Never present a `[CONV]` or `[OPINION]` claim as documented Apple guidance.
- Never claim an API exists, is available on a given OS version, or is
  deprecated without `[API]`-grade evidence.
- If the honest answer is "Apple doesn't say", say that — then give the best
  `[REC]` with its reasoning.

## Citation Format in Output

Inline, at the point of the claim:

    Sidebars collapse to a tab bar in compact width — `[HIG]` HIG > Tab bars
    (High). Use `NavigationSplitView` and let the system adapt — `[REC]`
    grounded in the above (High).
