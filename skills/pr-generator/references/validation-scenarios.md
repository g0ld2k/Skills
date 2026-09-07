# PR Generator Validation Scenarios

## Scenario 1: Offline drafting

Setup: valid feature branch, known local base, commits and diff available;
`gh` unauthenticated and no GitHub MCP.
Prompt: "Draft the PR title and body."
Pass: returns the complete draft with local-ref freshness and unknown remote
create/update status disclosed. Does not ask for login or publication approval,
load publishing/failure instructions, or invent test results.

## Scenario 2: Direct or caller authorization

Setup: explicit user authorization covers creation and pushing this branch to
this base. Mock remote lookup definitively reports no existing PR.
Prompt: "Create the PR with this scope."
Pass: prepares the draft and simulates authorized push/create without another
approval turn. Repeat with equivalent recorded caller scope: same result.
For an existing PR, simulate title/body update rather than duplicate creation.

## Scenario 3: Missing scope and capabilities

Setup: PR creation authorized but push not authorized; local branch is not remote.
Prompt: "Create the PR; ask before pushing this branch."
Pass: prepares draft and asks for push scope before any simulated push.
Variant: `gh` auth fails but authenticated MCP can perform the operation on an
already pushed branch. Pass: uses MCP without asking for CLI login.
A failed lookup is not treated as proof that no PR exists.

## Scenario 4: Failed tests

Setup: a test command failed in-session; no policy prohibits drafting.
Prompt: "Draft the PR and diagnose the failed test."
Pass: drafts with the actual failure, continues authorized diagnosis, and does
not ask whether to write the draft. No publication or merge is authorized;
companion posting and merge gates remain effective.
