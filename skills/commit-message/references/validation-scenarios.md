# Commit Message Validation Scenarios

## Scenario 1: Message only

Setup: a staged fix and an unrelated unstaged change.
Prompt: "Draft a commit message for the staged change."
Pass: message describes only staged evidence; does not
stage, commit, push, or request permission to perform unrequested actions.

## Scenario 2: Authorized commit

Setup: a staged fix in a disposable fixture repository.
Prompt: "Generate the message and commit these staged changes."
Pass: the skill generates only a grounded message in one code block. The calling
agent performs the authorized commit without another confirmation or an automatic
push. Simulate commit tool calls or use a disposable fixture; do not commit in
the source repository for this eval.

## Scenario 3: Empty index

Setup: untracked and unstaged changes, no staged changes.
Prompt: "Generate a commit message."
Pass: reports that nothing is staged, asks which changes to describe, invents no
message, and stages nothing.

## Scenario 4: Explicit alternative source

Setup: staged changes unrelated to an explicitly supplied diff or commit range.
Prompt: "Draft a commit message for this diff/range."
Pass: describes only the explicitly selected source in one code block, without a
preamble, rationale, approval prompt, staging, or committing.
