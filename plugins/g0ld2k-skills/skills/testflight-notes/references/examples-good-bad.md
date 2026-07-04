# Good vs Bad Transformations

## Example 1

Raw commit:
`feat: add TimezoneBucket model and ManagementTimezonesTabView`

Bad note:
`NEW: Added TimezoneBucket model and ManagementTimezonesTabView.`

Good note:
`NEW: Timezones are now grouped into expandable buckets so large lists are easier to scan.`

## Example 2

Raw commits:
- `fix: restore scroll position in people editor`
- `fix: guard list reload during save`

Bad note:
`FIX: Added scroll guard and reload guard in people view model.`

Good note:
`FIX: Scroll position no longer jumps when you save changes in the People editor.`

## Example 3

Raw commit:
`refactor: extract sync scheduler`

Bad note:
`IMPROVED: Refactored scheduler architecture.`

Good handling:
Omit unless there is explicit user-visible impact.

## Example 4

Raw commits:
- `feat(macOS): add global shortcut to quick panel`
- `fix(macOS): shortcut conflict when app inactive`

Bad note:
`NEW (macOS): Added shortcut and fixed conflict.`

Good note:
`NEW (macOS): You can open the quick panel from anywhere with a global keyboard shortcut.`

## Example 5

Raw commit:
`chore: update dependencies and snapshot tests`

Good handling:
Omit from TestFlight notes.
