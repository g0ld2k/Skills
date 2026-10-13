# PR writing conventions

Use the user's requested structure or repository template first. Otherwise lead
with the concrete problem and resulting behavior. A small change usually needs
one or two sentences plus relevant validation; use sections for complex work.
Do not require file counts, fixed bullet counts, empty risk sections, or a visual
that adds no information.

Prefer a Conventional Commit title such as `fix(sync): avoid duplicate replay`.
Use an optional scope when one subsystem dominates, and a breaking marker only
for demonstrated compatibility impact. A title around 72 characters is a useful
preference, not a hard gate.

Explain what changed and why it matters to a reviewer who has not seen the
conversation. Describe the final implementation, removing stale claims after
scope changes. Include material risks, migrations, screenshots, or manual checks
when relevant. Avoid repeating the file list already visible in GitHub.

Validation must distinguish modified tests from tests actually executed. Include
commands and outcomes that support the change. Say when checks were not run or
failed; never imply that adding a test proves it passed. Prior CI results may be
cited with their commit and scope, but are not tests run in the current session.
