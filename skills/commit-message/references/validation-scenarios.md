# Commit Message Validation Scenarios

These scenarios score behavior rather than prose.

## Scenario 1: Happy path — stable commit

Setup: A repository has staged changes with parent P and staged tree T. Both
remain stable while the exact displayed message is approved.

Prompt: Draft and commit a Conventional Commit message.

Pass: Evidence comes from the immutable P-to-T diff. The message, P, and T are
displayed together; parent, tree, and merge state are rechecked, `commit-tree`
receives P and T, and `update-ref` atomically expects P. The installed object's
message bytes equal the approved file before success is reported.

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

## Scenario 4: Initial commit

Setup: `HEAD` is symbolic but unborn, and tree T is staged.

Pass: Parent identity is `unborn:<ref>`, while a separate empty-tree OID is the
left side of the evidence diff. The sentinel is never passed as a Git revision.

## Scenario 5: Functional presentation change

Setup: Staged CSS changes alter visible layout or colors rather than whitespace.

Pass: The message is not classified as `style`; it selects the evidenced
functional type even though the changed file is presentation code.

## Scenario 6: Identity-mutating hooks

Setup: `message+commit` finds an active `pre-commit`, `prepare-commit-msg`, or
`commit-msg` hook and has no policy proving it preserves tree and message.

Pass: Automation does not invoke `git commit` or `--no-verify`. It blocks with
the hook path and requests a human/policy-specific flow that can authorize the
post-hook identity.

## Scenario 7: Ref movement and cleanup configuration

Setup: After final checks, another process moves the approved head ref, while
`commit.cleanup` would strip comment or scissors-like lines from the message.

Pass: The candidate is constructed from the approved parent/tree with the
exact message bytes. The conditional ref update fails against the moved parent,
so no live ref points to it; cleanup configuration never transforms the draft.

## Scenario 8: Sequencer, hook, and signing policy

Setup: A cherry-pick/revert/sequencer marker is active, an executable
`post-commit` hook exists, or policy requires signed commits.

Pass: Operation state blocks the ordinary workflow. The plumbing path does not
bypass a required hook. Signing mode and key are approved with the identity;
the signed candidate is verified before installation, and unresolved or failed
signing blocks.

## Scenario 9: Detached HEAD changes state

Setup: Approval records detached HEAD at P. Before installation, HEAD becomes
symbolic to a branch that also points at P.

Pass: Revalidation rejects the state change. Even if it occurs after the final
check, `update-ref --no-deref HEAD ... P` cannot advance the referenced branch.
