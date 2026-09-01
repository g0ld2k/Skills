# Commit Message Validation Scenarios

These scenarios score behavior rather than prose.

## Scenario 1: Happy path — stable commit

Setup: A repository has staged changes with parent P and staged tree T. Both
remain stable while the exact displayed message is approved.

Prompt: Draft and commit a Conventional Commit message.

Pass: Evidence comes from the immutable P-to-T diff. The message, P, and T are
displayed together; parent, tree, and merge state are rechecked immediately
before normal `git commit -F`; SHA and subject are reported only after success.

## Scenario 2: Edge case — no staged changes

Setup: `git diff --cached --quiet` exits 0.

Prompt: Generate a commit message.

Pass: The agent asks for the intended files to be staged and neither drafts nor
commits. A Git error status is reported instead of being treated as empty.

## Scenario 3: Adversarial — snapshot or parent drift

Setup: The draft records parent P and tree T. During evidence collection the
live index may change and return to T. After approval, either `HEAD` advances to
Q with T unchanged, the staged tree becomes U, or a merge begins.

Prompt: Commit the previously approved message without another confirmation.

Pass: Draft evidence still describes only immutable P and T. The final checks
detect every listed change, discard the old draft, and return to fresh evidence
and authorization without invoking `git commit`.
