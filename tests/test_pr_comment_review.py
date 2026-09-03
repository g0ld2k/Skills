#!/usr/bin/env python3
"""Behavior tests for PR comment reply safety."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / "skills" / "pr-comment-review" / "scripts"


class PostPRRepliesTests(unittest.TestCase):
    def run_dry_run(
        self,
        unresolved: list[dict[str, object]],
        replies: list[dict[str, object]],
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="pr-comment-review-test-") as temp:
            temp_path = Path(temp)
            scripts_path = temp_path / "scripts"
            bin_path = temp_path / "bin"
            scripts_path.mkdir()
            bin_path.mkdir()

            shutil.copy2(SKILL_SCRIPTS / "post_pr_replies.sh", scripts_path)
            shutil.copy2(SKILL_SCRIPTS / "common.sh", scripts_path)

            fake_fetch = scripts_path / "fetch_unresolved_review_comments.sh"
            fake_fetch.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    output=""
                    while [[ $# -gt 0 ]]; do
                      if [[ "$1" == "--output" ]]; then output="$2"; shift 2; else shift; fi
                    done
                    printf '%s\\n' '{json.dumps(unresolved)}' > "$output"
                    """
                )
            )
            fake_fetch.chmod(fake_fetch.stat().st_mode | stat.S_IXUSR)

            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    comment_id=101
                    if [[ "$*" == *"id=PRRT_two"* ]]; then comment_id=202; fi
                    if [[ "$*" == *"id=PRRT_resolved"* ]]; then comment_id=303; fi
                    is_resolved=false
                    if [[ "$*" == *"id=PRRT_resolved"* ]]; then is_resolved=true; fi
                    cat <<JSON
                    {"data":{"node":{"isResolved":IS_RESOLVED,"pullRequest":{"number":7,"repository":{"owner":{"login":"g0ld2k"},"name":"Skills"}},"comments":{"nodes":[{"databaseId":COMMENT_ID,"replyTo":null}]}}}}
                    JSON
                    """
                )
                .replace("COMMENT_ID", "$comment_id")
                .replace("IS_RESOLVED", "$is_resolved")
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            replies_path = temp_path / "replies.json"
            replies_path.write_text(json.dumps(replies))

            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            return subprocess.run(
                [
                    "bash",
                    str(scripts_path / "post_pr_replies.sh"),
                    "--owner",
                    "g0ld2k",
                    "--repo",
                    "Skills",
                    "--pr",
                    "7",
                    "--replies-file",
                    str(replies_path),
                    "--dry-run",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

    def test_dry_run_rejects_incomplete_unresolved_thread_inventory(self) -> None:
        """Removing this inventory check would allow a silently omitted reply."""
        unresolved = [
            {"thread_id": "PRRT_one", "comment_id": 101},
            {"thread_id": "PRRT_two", "comment_id": 202},
        ]
        replies = [
            {"thread_id": "PRRT_one", "comment_id": 101, "body": "Addressed."}
        ]

        result = self.run_dry_run(unresolved, replies)

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("reply inventory does not match", result.stderr)
        self.assertNotIn("would reply", result.stdout)

    def test_dry_run_accepts_exact_unresolved_thread_inventory(self) -> None:
        """An exact batch must still reach each per-thread dry-run check."""
        unresolved = [
            {"thread_id": "PRRT_one", "comment_id": 101},
            {"thread_id": "PRRT_two", "comment_id": 202},
        ]
        replies = [
            {"thread_id": "PRRT_one", "comment_id": 101, "body": "Addressed."},
            {"thread_id": "PRRT_two", "comment_id": 202, "body": "Addressed."},
        ]

        result = self.run_dry_run(unresolved, replies)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("DRY RUN: would reply"), 2)
        self.assertIn("would_post=2", result.stdout)

    def test_dry_run_rejects_missing_or_invalid_reply_body(self) -> None:
        """Invalid bodies must fail before any reply can be posted."""
        unresolved = [{"thread_id": "PRRT_one", "comment_id": 101}]
        invalid_replies = [
            {"thread_id": "PRRT_one", "comment_id": 101},
            {"thread_id": "PRRT_one", "comment_id": 101, "body": None},
            {"thread_id": "PRRT_one", "comment_id": 101, "body": 42},
            {"thread_id": "PRRT_one", "comment_id": 101, "body": ""},
        ]

        for replies in invalid_replies:
            with self.subTest(replies=replies):
                result = self.run_dry_run(unresolved, [replies])

                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("nonempty string body", result.stderr)
                self.assertNotIn("would reply", result.stdout)

    def test_dry_run_skips_surplus_reply_for_newly_resolved_thread(self) -> None:
        """Exact equality would block the existing resolved-thread race path."""
        unresolved = [{"thread_id": "PRRT_one", "comment_id": 101}]
        replies = [
            {"thread_id": "PRRT_one", "comment_id": 101, "body": "Addressed."},
            {
                "thread_id": "PRRT_resolved",
                "comment_id": 303,
                "body": "Addressed.",
            },
        ]

        result = self.run_dry_run(unresolved, replies)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("would_post=1", result.stdout)
        self.assertIn("skipped=1", result.stdout)
        self.assertIn("thread PRRT_resolved already resolved", result.stdout)

    def test_post_rejects_reply_bytes_changed_after_preview_approval(self) -> None:
        """Approval covers the canonical target and body, not a mutable file."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-approval-") as temp:
            temp_path = Path(temp)
            scripts_path = temp_path / "scripts"
            bin_path = temp_path / "bin"
            scripts_path.mkdir()
            bin_path.mkdir()
            for name in ("post_pr_replies.sh", "common.sh"):
                shutil.copy2(SKILL_SCRIPTS / name, scripts_path)

            fetch = scripts_path / "fetch_unresolved_review_comments.sh"
            fetch.write_text(
                "#!/usr/bin/env bash\n"
                "while [[ $# -gt 0 ]]; do "
                "if [[ $1 == --output ]]; then output=$2; shift 2; else shift; fi; "
                "done\n"
                "printf '%s\\n' '[{\"thread_id\":\"PRRT_one\",\"comment_id\":101}]' > \"$output\"\n"
            )
            fetch.chmod(fetch.stat().st_mode | stat.S_IXUSR)

            post_log = temp_path / "posts.log"
            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ $* == *' -X POST '* ]]; then echo POST >> \"$FAKE_POST_LOG\"; exit 0; fi\n"
                "printf '%s\\n' '{\"data\":{\"node\":{\"isResolved\":false,\"pullRequest\":{\"number\":7,\"repository\":{\"owner\":{\"login\":\"g0ld2k\"},\"name\":\"Skills\"}},\"comments\":{\"nodes\":[{\"databaseId\":101,\"replyTo\":null}]}}}}'\n"
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            replies_path = temp_path / "replies.json"
            preview_path = temp_path / "preview.json"
            replies_path.write_text(
                json.dumps(
                    [{"thread_id": "PRRT_one", "comment_id": 101, "body": "A"}]
                )
            )
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            environment["FAKE_POST_LOG"] = str(post_log)
            base = [
                "bash",
                str(scripts_path / "post_pr_replies.sh"),
                "--owner",
                "g0ld2k",
                "--repo",
                "Skills",
                "--pr",
                "7",
                "--replies-file",
                str(replies_path),
                "--preview-file",
                str(preview_path),
            ]
            preview = subprocess.run(
                [*base, "--dry-run"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
            digest_match = re.search(r"sha256:[0-9a-f]{64}", preview.stdout)
            self.assertIsNotNone(digest_match)

            replies_path.write_text(
                json.dumps(
                    [{"thread_id": "PRRT_one", "comment_id": 101, "body": "B"}]
                )
            )
            result = subprocess.run(
                [*base, "--approved-digest", digest_match.group(0)],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("approval preview", result.stderr)
            self.assertFalse(post_log.exists())

    def test_post_sends_large_body_through_json_input(self) -> None:
        """The reply body must not enter the GitHub client's argument list."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-payload-") as temp:
            temp_path = Path(temp)
            scripts_path = temp_path / "scripts"
            bin_path = temp_path / "bin"
            scripts_path.mkdir()
            bin_path.mkdir()
            for name in ("post_pr_replies.sh", "common.sh"):
                shutil.copy2(SKILL_SCRIPTS / name, scripts_path)

            fetch = scripts_path / "fetch_unresolved_review_comments.sh"
            fetch.write_text(
                "#!/usr/bin/env bash\n"
                "while [[ $# -gt 0 ]]; do "
                "if [[ $1 == --output ]]; then output=$2; shift 2; else shift; fi; "
                "done\n"
                "printf '%s\\n' '[{\"thread_id\":\"PRRT_one\",\"comment_id\":101}]' > \"$output\"\n"
            )
            fetch.chmod(fetch.stat().st_mode | stat.S_IXUSR)

            marker = "BODY_SENT_VIA_INPUT"
            post_log = temp_path / "posts.log"
            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ "$*" == *" -X POST "* ]]; then
                      input=""
                      previous=""
                      for argument in "$@"; do
                        [[ "$argument" != *"$BODY_MARKER"* ]] || exit 41
                        if [[ "$previous" == "--input" ]]; then input="$argument"; fi
                        previous="$argument"
                      done
                      [[ -n "$input" ]] || exit 42
                      grep -F "$BODY_MARKER" "$input" >/dev/null
                      echo POST >> "$FAKE_POST_LOG"
                      exit 0
                    fi
                    printf '%s\n' '{"data":{"node":{"isResolved":false,"pullRequest":{"number":7,"repository":{"owner":{"login":"g0ld2k"},"name":"Skills"}},"comments":{"nodes":[{"databaseId":101,"replyTo":null}]}}}}'
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            replies_path = temp_path / "replies.json"
            preview_path = temp_path / "preview.json"
            replies_path.write_text(
                json.dumps(
                    [
                        {
                            "thread_id": "PRRT_one",
                            "comment_id": 101,
                            "body": "x" * 200_000 + marker,
                        }
                    ]
                )
            )
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            environment["BODY_MARKER"] = marker
            environment["FAKE_POST_LOG"] = str(post_log)
            base = [
                "bash",
                str(scripts_path / "post_pr_replies.sh"),
                "--owner",
                "g0ld2k",
                "--repo",
                "Skills",
                "--pr",
                "7",
                "--replies-file",
                str(replies_path),
                "--preview-file",
                str(preview_path),
            ]
            preview = subprocess.run(
                [*base, "--dry-run"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            digest = re.search(r"sha256:[0-9a-f]{64}", preview.stdout)
            self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
            self.assertIsNotNone(digest)
            result = subprocess.run(
                [*base, "--approved-digest", digest.group(0)],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(post_log.read_text().strip(), "POST")

    def test_post_rechecks_complete_inventory_before_each_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pr-comment-drift-") as temp:
            temp_path = Path(temp)
            scripts_path = temp_path / "scripts"
            bin_path = temp_path / "bin"
            scripts_path.mkdir()
            bin_path.mkdir()
            for name in ("post_pr_replies.sh", "common.sh"):
                shutil.copy2(SKILL_SCRIPTS / name, scripts_path)

            fetch_count = temp_path / "fetch-count"
            fetch_count.write_text("0")
            fetch = scripts_path / "fetch_unresolved_review_comments.sh"
            fetch.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    while [[ $# -gt 0 ]]; do
                      if [[ $1 == --output ]]; then output=$2; shift 2; else shift; fi
                    done
                    count="$(<"$FETCH_COUNT")"
                    if ((count < 3)); then
                      body='[{"thread_id":"PRRT_one","comment_id":101},{"thread_id":"PRRT_two","comment_id":202}]'
                    else
                      body='[{"thread_id":"PRRT_one","comment_id":101},{"thread_id":"PRRT_two","comment_id":202},{"thread_id":"PRRT_new","comment_id":303}]'
                    fi
                    printf '%s\n' "$body" > "$output"
                    echo $((count + 1)) > "$FETCH_COUNT"
                    """
                )
            )
            fetch.chmod(fetch.stat().st_mode | stat.S_IXUSR)

            post_log = temp_path / "posts.log"
            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ "$*" == *" -X POST "* ]]; then echo POST >> "$POST_LOG"; exit 0; fi
                    comment_id=101
                    [[ "$*" != *"id=PRRT_two"* ]] || comment_id=202
                    cat <<JSON
                    {"data":{"node":{"isResolved":false,"pullRequest":{"number":7,"repository":{"owner":{"login":"g0ld2k"},"name":"Skills"}},"comments":{"nodes":[{"databaseId":$comment_id,"replyTo":null}]}}}}
                    JSON
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            replies = temp_path / "replies.json"
            preview = temp_path / "preview.json"
            replies.write_text(json.dumps([
                {"thread_id": "PRRT_one", "comment_id": 101, "body": "One"},
                {"thread_id": "PRRT_two", "comment_id": 202, "body": "Two"},
            ]))
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            environment["FETCH_COUNT"] = str(fetch_count)
            environment["POST_LOG"] = str(post_log)
            base = ["bash", str(scripts_path / "post_pr_replies.sh"), "--owner", "g0ld2k", "--repo", "Skills", "--pr", "7", "--replies-file", str(replies), "--preview-file", str(preview)]
            dry_run = subprocess.run([*base, "--dry-run"], capture_output=True, text=True, env=environment)
            digest = re.search(r"sha256:[0-9a-f]{64}", dry_run.stdout)
            self.assertEqual(dry_run.returncode, 0, dry_run.stdout + dry_run.stderr)
            self.assertIsNotNone(digest)

            result = subprocess.run([*base, "--approved-digest", digest.group(0)], capture_output=True, text=True, env=environment)

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(post_log.read_text().splitlines(), ["POST"])

    def test_dry_run_fails_without_a_sha256_tool(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pr-comment-hash-") as temp:
            temp_path = Path(temp)
            scripts_path = temp_path / "scripts"
            bin_path = temp_path / "bin"
            scripts_path.mkdir()
            bin_path.mkdir()
            for name in ("post_pr_replies.sh", "common.sh"):
                shutil.copy2(SKILL_SCRIPTS / name, scripts_path)
            for command in ("bash", "dirname", "jq", "awk", "mktemp", "rm", "cp"):
                target = shutil.which(command)
                self.assertIsNotNone(target)
                (bin_path / command).symlink_to(target)
            fake_gh = bin_path / "gh"
            fake_gh.write_text("#!/usr/bin/env bash\nexit 98\n")
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)
            fetch = scripts_path / "fetch_unresolved_review_comments.sh"
            fetch.write_text("#!/usr/bin/env bash\nexit 99\n")
            fetch.chmod(fetch.stat().st_mode | stat.S_IXUSR)
            replies = temp_path / "replies.json"
            replies.write_text(json.dumps([{"thread_id": "PRRT_one", "comment_id": 101, "body": "One"}]))
            environment = os.environ.copy()
            environment["PATH"] = str(bin_path)

            result = subprocess.run(
                [str(bin_path / "bash"), str(scripts_path / "post_pr_replies.sh"), "--owner", "g0ld2k", "--repo", "Skills", "--pr", "7", "--replies-file", str(replies), "--dry-run"],
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("DRY RUN DIGEST: sha256:\n", result.stdout)
            self.assertIn("SHA-256 utility is required", result.stderr)


class FetchReviewThreadsTests(unittest.TestCase):
    def run_fetch(self, responses: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="pr-comment-fetch-") as temp:
            temp_path = Path(temp)
            bin_path = temp_path / "bin"
            bin_path.mkdir()
            responses_path = temp_path / "responses"
            responses_path.mkdir()
            for index, response in enumerate(responses):
                (responses_path / f"{index}.json").write_text(json.dumps(response))
            counter_path = temp_path / "counter"
            counter_path.write_text("0")
            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    index="$(<"$FAKE_COUNTER")"
                    response="$FAKE_RESPONSES/$index.json"
                    [[ -f "$response" ]] || exit 90
                    cat "$response"
                    echo $((index + 1)) > "$FAKE_COUNTER"
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            environment["FAKE_COUNTER"] = str(counter_path)
            environment["FAKE_RESPONSES"] = str(responses_path)
            return subprocess.run(
                [
                    "bash",
                    str(SKILL_SCRIPTS / "fetch_unresolved_review_comments.sh"),
                    "g0ld2k",
                    "Skills",
                    "7",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

    @staticmethod
    def page(comment_id: int, thread_id: str, has_next: bool) -> dict[str, object]:
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": thread_id,
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "databaseId": comment_id,
                                                "id": f"node-{comment_id}",
                                                "body": "Review body",
                                                "path": f"file-{comment_id}.py",
                                                "line": 1,
                                                "originalLine": 1,
                                                "url": f"https://example.test/discussion_r{comment_id}",
                                                "createdAt": "2026-09-01T00:00:00Z",
                                                "author": {"login": "reviewer"},
                                                "replyTo": None,
                                            }
                                        ],
                                        "pageInfo": {
                                            "hasNextPage": False,
                                            "endCursor": None,
                                        },
                                    },
                                }
                            ],
                            "pageInfo": {
                                "hasNextPage": has_next,
                                "endCursor": "NEXT" if has_next else None,
                            },
                        }
                    }
                }
            }
        }

    def test_fetch_exhausts_outer_thread_pages(self) -> None:
        """A later page must not disappear behind nested pagination metadata."""
        result = self.run_fetch(
            [self.page(101, "PRRT_one", True), self.page(202, "PRRT_two", False)]
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        inventory = json.loads(result.stdout)
        self.assertEqual(
            {(item["thread_id"], item["comment_id"]) for item in inventory},
            {("PRRT_one", 101), ("PRRT_two", 202)},
        )

    def test_fetch_rejects_errors_or_missing_pr_as_empty_inventory(self) -> None:
        """Lookup failures cannot masquerade as a PR with no review threads."""
        invalid_responses = [
            {"errors": [{"message": "Bad credentials"}], "data": {}},
            {"data": {"repository": {"pullRequest": None}}},
        ]
        for response in invalid_responses:
            with self.subTest(response=response):
                result = self.run_fetch([response])
                self.assertNotEqual(result.returncode, 0)
                self.assertNotEqual(result.stdout.strip(), "[]")

    def test_fetch_rejects_repeated_outer_cursor(self) -> None:
        result = self.run_fetch(
            [self.page(101, "PRRT_one", True), self.page(202, "PRRT_two", True)]
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cursor did not advance", result.stderr)

    def test_fetch_rejects_repeated_nested_cursor(self) -> None:
        outer = self.page(101, "PRRT_one", False)
        comments = outer["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0]["comments"]
        comments["pageInfo"] = {"hasNextPage": True, "endCursor": "COMMENT_NEXT"}
        nested = {
            "data": {
                "node": {
                    "comments": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": True, "endCursor": "COMMENT_NEXT"},
                    }
                }
            }
        }

        result = self.run_fetch([outer, nested])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cursor did not advance", result.stderr)


if __name__ == "__main__":
    unittest.main()
