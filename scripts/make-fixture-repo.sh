#!/usr/bin/env bash
set -euo pipefail

target="$(mktemp -d "${TMPDIR:-/tmp}/skill-fixture.XXXXXX")"
git -C "$target" init -q -b main
git -C "$target" config user.email fixture@example.com
git -C "$target" config user.name Fixture
git -C "$target" config commit.gpgsign false
git -C "$target" config core.hooksPath /dev/null
git -C "$target" config tag.gpgSign false
# Pin dates so commit hashes are identical across runs:
export GIT_AUTHOR_DATE="2026-01-01T00:00:00Z" GIT_COMMITTER_DATE="2026-01-01T00:00:00Z"

commit() { git -C "$target" add -A && git -C "$target" commit -q --no-verify -m "$1"; }

mkdir -p "$target/Sources/App" "$target/Tests/AppTests"
echo 'struct Session {}' > "$target/Sources/App/Session.swift"
commit "feat(auth): add session model"
echo 'final class SessionTests {}' > "$target/Tests/AppTests/SessionTests.swift"
commit "test: add session tests"
git -C "$target" tag build-1
echo '// retry on 401' >> "$target/Sources/App/Session.swift"
commit "fix(auth): retry token refresh on 401"
echo 'let cache: [String: String] = [:]' > "$target/Sources/App/Cache.swift"
commit "chore: update dependencies and snapshot tests"
# Leave one staged, uncommitted change for commit-message scenarios:
echo '// rotate refresh tokens' >> "$target/Sources/App/Session.swift"
git -C "$target" add Sources/App/Session.swift

echo "$target"
