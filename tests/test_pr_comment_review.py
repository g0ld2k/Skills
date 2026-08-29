#!/usr/bin/env python3
"""Behavior tests for PR comment reply safety."""

from __future__ import annotations

import json
import os
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


if __name__ == "__main__":
    unittest.main()
