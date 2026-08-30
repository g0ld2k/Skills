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

    def test_reply_iterator_failure_is_reported(self) -> None:
        """A failed replies-file iterator must not look like a clean empty run."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-reply-iterator-test-") as temp:
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
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    output=""
                    while [[ $# -gt 0 ]]; do
                      if [[ "$1" == "--output" ]]; then output="$2"; shift 2; else shift; fi
                    done
                    printf '%s\\n' '[{"thread_id":"PRRT_one","comment_id":101}]' > "$output"
                    """
                )
            )
            fake_fetch.chmod(fake_fetch.stat().st_mode | stat.S_IXUSR)

            real_jq = shutil.which("jq")
            self.assertIsNotNone(real_jq)
            fake_jq = bin_path / "jq"
            fake_jq.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ "${{1:-}}" == "-c" &&
                          ( "${{2:-}}" == ".[]" ||
                            "${{2:-}}" == ".[] | select(.isResolved == false)" ) ]]; then
                      echo "simulated replies-file iterator failure" >&2
                      exit 42
                    fi
                    exec '{real_jq}' "$@"
                    """
                )
            )
            fake_jq.chmod(fake_jq.stat().st_mode | stat.S_IXUSR)

            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    echo "gh must not be called after iterator failure" >&2
                    exit 99
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            replies_path = temp_path / "replies.json"
            replies_path.write_text(
                json.dumps(
                    [{"thread_id": "PRRT_one", "comment_id": 101, "body": "Addressed."}]
                )
            )
            result = subprocess.run(
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
                ],
                check=False,
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": f"{bin_path}:{os.environ['PATH']}"},
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("simulated replies-file iterator failure", result.stderr)

    def test_temp_allocation_failure_cleans_earlier_files(self) -> None:
        """A later mktemp failure must not leak the first allocation."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-post-mktemp-test-") as temp:
            temp_path = Path(temp)
            bin_path = temp_path / "bin"
            temp_dir = temp_path / "tmp"
            bin_path.mkdir()
            temp_dir.mkdir()

            real_mktemp = shutil.which("mktemp")
            self.assertIsNotNone(real_mktemp)
            state_path = temp_path / "mktemp-state"
            fake_mktemp = bin_path / "mktemp"
            fake_mktemp.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ -e '{state_path}' ]]; then
                      echo "simulated post mktemp failure" >&2
                      exit 42
                    fi
                    : > '{state_path}'
                    exec '{real_mktemp}' "$@"
                    """
                )
            )
            fake_mktemp.chmod(fake_mktemp.stat().st_mode | stat.S_IXUSR)

            replies_path = temp_path / "replies.json"
            replies_path.write_text("[]")
            result = subprocess.run(
                [
                    "bash",
                    str(SKILL_SCRIPTS / "post_pr_replies.sh"),
                    "--owner",
                    "g0ld2k",
                    "--repo",
                    "Skills",
                    "--pr",
                    "7",
                    "--replies-file",
                    str(replies_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "PATH": f"{bin_path}:{os.environ['PATH']}",
                    "TMPDIR": str(temp_dir),
                },
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("simulated post mktemp failure", result.stderr)
            self.assertEqual(list(temp_dir.glob("post-replies-*")), [])


class FetchUnresolvedReviewCommentsTests(unittest.TestCase):
    def test_thread_iterator_failure_is_reported(self) -> None:
        """A failed unresolved-thread enumeration must not look like an empty result."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-iterator-test-") as temp:
            temp_path = Path(temp)
            bin_path = temp_path / "bin"
            bin_path.mkdir()

            response_path = temp_path / "response.json"
            response_path.write_text(
                json.dumps(
                    {
                        "data": {
                            "repository": {
                                "pullRequest": {
                                    "reviewThreads": {
                                        "nodes": [],
                                        "pageInfo": {
                                            "hasNextPage": False,
                                            "endCursor": None,
                                        },
                                    }
                                }
                            }
                        }
                    }
                )
            )
            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    cat '{response_path}'
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            real_jq = shutil.which("jq")
            self.assertIsNotNone(real_jq)
            fake_jq = bin_path / "jq"
            fake_jq.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ "${{1:-}}" == "-c" &&
                          ( "${{2:-}}" == ".[]" ||
                            "${{2:-}}" == ".[] | select(.isResolved == false)" ) ]]; then
                      echo "simulated unresolved-thread enumeration failure" >&2
                      exit 42
                    fi
                    exec '{real_jq}' "$@"
                    """
                )
            )
            fake_jq.chmod(fake_jq.stat().st_mode | stat.S_IXUSR)

            result = subprocess.run(
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
                env={**os.environ, "PATH": f"{bin_path}:{os.environ['PATH']}"},
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("simulated unresolved-thread enumeration failure", result.stderr)

    def test_temp_allocation_failure_cleans_earlier_files(self) -> None:
        """A later mktemp failure must not leak the first allocation."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-fetch-mktemp-test-") as temp:
            temp_path = Path(temp)
            bin_path = temp_path / "bin"
            temp_dir = temp_path / "tmp"
            bin_path.mkdir()
            temp_dir.mkdir()

            real_mktemp = shutil.which("mktemp")
            self.assertIsNotNone(real_mktemp)
            state_path = temp_path / "mktemp-state"
            fake_mktemp = bin_path / "mktemp"
            fake_mktemp.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ -e '{state_path}' ]]; then
                      echo "simulated fetch mktemp failure" >&2
                      exit 42
                    fi
                    : > '{state_path}'
                    exec '{real_mktemp}' "$@"
                    """
                )
            )
            fake_mktemp.chmod(fake_mktemp.stat().st_mode | stat.S_IXUSR)

            result = subprocess.run(
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
                env={
                    **os.environ,
                    "PATH": f"{bin_path}:{os.environ['PATH']}",
                    "TMPDIR": str(temp_dir),
                },
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("simulated fetch mktemp failure", result.stderr)
            self.assertEqual(list(temp_dir.glob("fetch-*")), [])

    def test_pagination_includes_follow_up_replies(self) -> None:
        """A thread with more than one comments page keeps every reply."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-follow-up-test-") as temp:
            temp_path = Path(temp)
            bin_path = temp_path / "bin"
            bin_path.mkdir()

            root = {
                "databaseId": 101,
                "id": "PRRC_root",
                "body": "root",
                "path": "file.swift",
                "line": 10,
                "originalLine": 10,
                "url": "https://github.com/g0ld2k/Skills/pull/7#discussion_r101",
                "createdAt": "2026-08-30T00:00:00Z",
                "author": {"login": "reviewer"},
                "replyTo": None,
            }
            reply = {
                "databaseId": 102,
                "id": "PRRC_reply",
                "body": "reply",
                "path": "file.swift",
                "line": 10,
                "originalLine": 10,
                "url": "https://github.com/g0ld2k/Skills/pull/7#discussion_r102",
                "createdAt": "2026-08-30T00:01:00Z",
                "author": {"login": "author"},
                "replyTo": {"id": "PRRC_root"},
            }
            outer_response = {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "nodes": [
                                    {
                                        "id": "PRRT_one",
                                        "isResolved": False,
                                        "comments": {
                                            "nodes": [root],
                                            "pageInfo": {
                                                "hasNextPage": True,
                                                "endCursor": "comments-1",
                                            },
                                        },
                                    }
                                ],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            }
                        }
                    }
                }
            }
            follow_up_response = {
                "data": {
                    "node": {
                        "comments": {
                            "nodes": [reply],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
            outer_path = temp_path / "outer.json"
            outer_path.write_text(json.dumps(outer_response))
            follow_up_path = temp_path / "follow-up.json"
            follow_up_path.write_text(json.dumps(follow_up_response))

            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ "$*" == *"-F id=PRRT_one"* ]]; then
                      cat '{follow_up_path}'
                    else
                      cat '{outer_path}'
                    fi
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            output_path = temp_path / "unresolved.json"
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            result = subprocess.run(
                [
                    "bash",
                    str(SKILL_SCRIPTS / "fetch_unresolved_review_comments.sh"),
                    "g0ld2k",
                    "Skills",
                    "7",
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            fetched = json.loads(output_path.read_text())
            self.assertEqual(fetched[0]["replies"], [{
                "comment_id": 102,
                "author": "author",
                "body": "reply",
                "created_at": "2026-08-30T00:01:00Z",
            }])

    def test_pagination_cleans_extra_accumulator_on_enrichment_failure(self) -> None:
        """A failed thread enrichment must not leak its temporary accumulator."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-extra-cleanup-test-") as temp:
            temp_path = Path(temp)
            bin_path = temp_path / "bin"
            temp_dir = temp_path / "tmp"
            bin_path.mkdir()
            temp_dir.mkdir()

            root = {
                "databaseId": 101,
                "id": "PRRC_root",
                "body": "root",
                "path": "file.swift",
                "line": 10,
                "originalLine": 10,
                "url": "https://github.com/g0ld2k/Skills/pull/7#discussion_r101",
                "createdAt": "2026-08-30T00:00:00Z",
                "author": {"login": "reviewer"},
                "replyTo": None,
            }
            response_path = temp_path / "response.json"
            response_path.write_text(
                json.dumps(
                    {
                        "data": {
                            "repository": {
                                "pullRequest": {
                                    "reviewThreads": {
                                        "nodes": [
                                            {
                                                "id": "PRRT_one",
                                                "isResolved": False,
                                                "comments": {
                                                    "nodes": [root],
                                                    "pageInfo": {
                                                        "hasNextPage": False,
                                                        "endCursor": None,
                                                    },
                                                },
                                            }
                                        ],
                                        "pageInfo": {
                                            "hasNextPage": False,
                                            "endCursor": None,
                                        },
                                    }
                                }
                            }
                        }
                    }
                )
            )
            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    cat '{response_path}'
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            real_jq = shutil.which("jq")
            self.assertIsNotNone(real_jq)
            fake_jq = bin_path / "jq"
            fake_jq.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ "$*" == *"--slurpfile extra"* ]]; then
                      echo "simulated thread enrichment failure" >&2
                      exit 42
                    fi
                    exec '{real_jq}' "$@"
                    """
                )
            )
            fake_jq.chmod(fake_jq.stat().st_mode | stat.S_IXUSR)

            result = subprocess.run(
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
                env={
                    **os.environ,
                    "PATH": f"{bin_path}:{os.environ['PATH']}",
                    "TMPDIR": str(temp_dir),
                },
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("simulated thread enrichment failure", result.stderr)
            self.assertEqual(list(temp_dir.glob("fetch-extra.*")), [])

    def test_pagination_enriches_threads_incrementally(self) -> None:
        """Per-thread pagination must not rewrite the full thread document."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-fetch-test-") as temp:
            temp_path = Path(temp)
            bin_path = temp_path / "bin"
            bin_path.mkdir()

            threads = [
                {
                    "id": f"PRRT_{index}",
                    "isResolved": False,
                    "comments": {
                        "nodes": [
                            {
                                "databaseId": index + 1,
                                "id": f"PRRC_{index}",
                                "body": "root",
                                "path": "file.swift",
                                "line": index + 1,
                                "originalLine": index + 1,
                                "url": f"https://github.com/g0ld2k/Skills/pull/7#discussion_r{index + 1}",
                                "createdAt": "2026-08-30T00:00:00Z",
                                "author": {"login": "reviewer"},
                                "replyTo": None,
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    },
                }
                for index in range(120)
            ]
            first_response_path = temp_path / "first-response.json"
            first_response_path.write_text(
                json.dumps(
                    {
                        "data": {
                            "repository": {
                                "pullRequest": {
                                    "reviewThreads": {
                                        "nodes": threads[:100],
                                        "pageInfo": {
                                            "hasNextPage": True,
                                            "endCursor": "threads-1",
                                        },
                                    }
                                }
                            }
                        }
                    }
                )
            )
            second_response_path = temp_path / "second-response.json"
            second_response_path.write_text(
                json.dumps(
                    {
                        "data": {
                            "repository": {
                                "pullRequest": {
                                    "reviewThreads": {
                                        "nodes": threads[100:],
                                        "pageInfo": {
                                            "hasNextPage": False,
                                            "endCursor": None,
                                        },
                                    }
                                }
                            }
                        }
                    }
                )
            )

            gh_log = temp_path / "gh.log"
            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ "$*" == *"-F endCursor=null"* ]]; then
                      echo "null" >> '{gh_log}'
                      cat '{first_response_path}'
                    elif [[ "$*" == *"-F endCursor=threads-1"* ]]; then
                      echo "threads-1" >> '{gh_log}'
                      cat '{second_response_path}'
                    else
                      echo "unexpected pagination cursor" >&2
                      exit 64
                    fi
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            real_jq = shutil.which("jq")
            self.assertIsNotNone(real_jq)
            fake_jq = bin_path / "jq"
            fake_jq.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [[ "$*" == *"--argjson idx"* ]]; then
                      echo "full-document merge detected" >&2
                      exit 43
                    fi
                    exec '{real_jq}' "$@"
                    """
                )
            )
            fake_jq.chmod(fake_jq.stat().st_mode | stat.S_IXUSR)

            output_path = temp_path / "unresolved.json"
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            result = subprocess.run(
                [
                    "bash",
                    str(SKILL_SCRIPTS / "fetch_unresolved_review_comments.sh"),
                    "g0ld2k",
                    "Skills",
                    "7",
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            fetched = json.loads(output_path.read_text())
            self.assertEqual(len(fetched), len(threads))
            self.assertEqual(
                [comment["comment_id"] for comment in fetched], list(range(1, 121))
            )
            self.assertEqual(gh_log.read_text().splitlines(), ["null", "threads-1"])


class PostPRReplyPayloadTests(unittest.TestCase):
    def test_large_reply_body_is_sent_via_input_file(self) -> None:
        """Posting a large body must not put its contents into argv."""
        with tempfile.TemporaryDirectory(prefix="pr-comment-payload-test-") as temp:
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
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    output=""
                    while [[ $# -gt 0 ]]; do
                      if [[ "$1" == "--output" ]]; then output="$2"; shift 2; else shift; fi
                    done
                    printf '%s\\n' '[{"thread_id":"PRRT_one","comment_id":101}]' > "$output"
                    """
                )
            )
            fake_fetch.chmod(fake_fetch.stat().st_mode | stat.S_IXUSR)

            argv_log = temp_path / "argv.log"
            payload_log = temp_path / "payload.json"
            fake_gh = bin_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\\n' "$*" > '{argv_log}'
                    if [[ "$*" == *"-X POST"* ]]; then
                      input_file=""
                      while [[ $# -gt 0 ]]; do
                        if [[ "$1" == "--input" ]]; then input_file="$2"; shift 2; else shift; fi
                      done
                      test -n "$input_file"
                      cp "$input_file" '{payload_log}'
                    else
                      cat <<'JSON'
                    {{"data":{{"node":{{"isResolved":false,"pullRequest":{{"number":7,"repository":{{"owner":{{"login":"g0ld2k"}},"name":"Skills"}}}},"comments":{{"nodes":[{{"databaseId":101,"replyTo":null}}]}}}}}}}}
                    JSON
                    fi
                    """
                )
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

            large_body = "x" * 200_000
            replies_path = temp_path / "replies.json"
            replies_path.write_text(
                json.dumps(
                    [{"thread_id": "PRRT_one", "comment_id": 101, "body": large_body}]
                )
            )

            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            result = subprocess.run(
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
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn(large_body, argv_log.read_text())
            self.assertEqual(json.loads(payload_log.read_text()), {"body": large_body})


if __name__ == "__main__":
    unittest.main()
