#!/usr/bin/env python3
"""Exercise review helpers with recorded API shapes and mocked network writes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/pr-comment-review/scripts"


def comment(cid=101, body="Please fix this.", reply=False):
    return {"databaseId": cid, "id": f"C{cid}", "body": body, "path": "a.py",
            "line": 3, "url": f"https://github.com/g0ld2k/Skills/pull/7#discussion_r{cid}",
            "createdAt": "2026-10-04T00:00:00Z", "author": {"login": "reviewer"},
            "replyTo": {"id": "C101"} if reply else None}


def connection(nodes, more=False, cursor=None):
    return {"nodes": nodes, "pageInfo": {"hasNextPage": more, "endCursor": cursor}}


def thread(cid=101, resolved=False, comments=None):
    return {"id": f"T{cid}", "isResolved": resolved,
            "comments": connection([comment(cid)]) if comments is None else comments}


def outer(threads, more=False, cursor=None):
    return {"data": {"repository": {"pullRequest": {"reviewThreads": connection(threads, more, cursor)}}}}


def live(cid=101, resolved=False, comments=None):
    value = thread(cid, resolved, comments)
    value["pullRequest"] = {"number": 7, "repository": {"owner": {"login": "g0ld2k"}, "name": "Skills"}}
    return {"data": {"node": value}}


def reviewed(cid=101):
    return {"thread_id": f"T{cid}", "comment_id": cid, "body": "Please fix this.",
            "replies": [], "replies_truncated": False}


def reply(cid=101, body="Fixed and verified."):
    return {"thread_id": f"T{cid}", "comment_id": cid, "body": body}


def step(response=None, *, kind="graphql", fail=False):
    return {"kind": kind, "response": response, "fail": fail}


class HelperTests(unittest.TestCase):
    def run_helper(self, steps, *, replies=None, snapshot=None, raw=None, dry=False, fetch=False, existing_output=None):
        with tempfile.TemporaryDirectory(prefix="review-helpers-") as temp:
            path = Path(temp)
            (path / "steps.json").write_text(json.dumps(steps))
            fake = path / "gh"
            fake.write_text(f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
p = Path(os.environ["FAKE_GH_DIR"])
a = sys.argv[1:]
kind = "post" if "POST" in a else "graphql"
record = {"args": a, "kind": kind}
if "--input" in a:
    record["payload"] = json.loads(Path(a[a.index("--input") + 1]).read_text())
with (p / "calls.jsonl").open("a") as f:
    f.write(json.dumps(record) + "\\n")
i = int((p / "index").read_text()) if (p / "index").exists() else 0
steps = json.loads((p / "steps.json").read_text())
(p / "index").write_text(str(i + 1))
if i >= len(steps) or steps[i]["kind"] != kind:
    print("unexpected API call", file=sys.stderr)
    sys.exit(8)
s = steps[i]
for filename, content in s.get("mutations", {}).items():
    (p / filename).write_text(json.dumps(content))
if s["fail"]:
    print("mock API failure", file=sys.stderr)
    sys.exit(1)
if "stream" in s:
    for response in s["stream"]:
        print(json.dumps(response))
else:
    print(json.dumps(s["response"]))
''')
            fake.chmod(0o755)
            env = {**os.environ, "PATH": f"{path}:{os.environ['PATH']}", "FAKE_GH_DIR": temp}
            output = path / "output.json"
            if existing_output is not None:
                output.write_text(json.dumps(existing_output))
            if fetch:
                args = ["bash", str(SCRIPTS / "fetch_unresolved_review_comments.sh"), "g0ld2k", "Skills", "7", "--output", str(output)]
            else:
                (path / "replies.json").write_text(raw if raw is not None else json.dumps(replies if replies is not None else [reply()]))
                (path / "reviewed.json").write_text(json.dumps(snapshot if snapshot is not None else [reviewed()]))
                args = ["bash", str(SCRIPTS / "post_pr_replies.sh"), "--owner", "g0ld2k", "--repo", "Skills", "--pr", "7", "--replies-file", str(path / "replies.json"), "--reviewed-comments-file", str(path / "reviewed.json")]
                if dry:
                    args.append("--dry-run")
            result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=15)
            calls = [json.loads(line) for line in (path / "calls.jsonl").read_text().splitlines()] if (path / "calls.jsonl").exists() else []
            value = json.loads(output.read_text()) if output.exists() else None
            return result, calls, value

    def assert_blocked(self, result, calls):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any(c["kind"] == "post" for c in calls), calls)

    def test_fetch_outer_and_nested_pages(self):
        first = thread(comments=connection([comment()], True, "reply-next"))
        result, calls, value = self.run_helper([
            step(outer([first], True, "thread-next")), step(outer([thread(202)])),
            step({"data": {"node": {"comments": connection([comment(102, "More context", True)])}}})], fetch=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([v["comment_id"] for v in value], [101, 202])
        self.assertEqual(value[0]["replies"][0]["body"], "More context")
        self.assertFalse(value[0]["replies_truncated"])
        self.assertIn("endCursor=thread-next", calls[1]["args"])
        self.assertIn("endCursor=reply-next", calls[2]["args"])

    def test_fetch_rejects_multiple_response_documents(self):
        for documents in ([{"errors": [{"message": "denied"}]}, outer([thread()])],
                          [outer([thread()]), outer([thread(202)])]):
            result, _, value = self.run_helper([{**step(), "stream": documents}], fetch=True, existing_output=[reviewed()])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(value, [reviewed()])

    def test_live_lookup_rejects_multiple_response_documents(self):
        result, calls, _ = self.run_helper([step(outer([thread()])),
            {**step(), "stream": [{"errors": [{"message": "denied"}]}, live()]}])
        self.assert_blocked(result, calls)

    def test_fetch_empty_is_success(self):
        result, _, value = self.run_helper([step(outer([]))], fetch=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(value, [])

    def test_fetch_rejects_errors_null_and_bad_shapes(self):
        broken = [None, {"data": {"repository": None}}, {"data": {"repository": {"pullRequest": None}}},
                  {"errors": [{"message": "denied"}], **outer([])}, outer([{"id": "T101", "isResolved": False}]),
                  outer([thread(comments=connection([]))]), outer([thread(comments=connection([comment(102, reply=True)]))])]
        for response in broken:
            with self.subTest(response=response):
                result, _, value = self.run_helper([step(response)], fetch=True)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIsNone(value)

    def test_fetch_rejects_stalled_or_missing_outer_cursor(self):
        for cursor in (None, "", "again"):
            with self.subTest(cursor=cursor):
                result, _, value = self.run_helper([step(outer([], True, cursor)), step(outer([], True, cursor))], fetch=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(value)

    def test_nested_failure_never_returns_partial_success(self):
        first = thread(comments=connection([comment()], True, "again"))
        for next_step in (step(fail=True), step({"data": {"node": None}}), step({"data": {"node": {"comments": connection([], True, "again")}}})):
            with self.subTest(next_step=next_step):
                result, _, value = self.run_helper([step(outer([first])), next_step], fetch=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(value)

    def test_root_id_falls_back_to_github_discussion_fragment(self):
        root = comment()
        root["databaseId"] = None
        result, _, value = self.run_helper([step(outer([thread(comments=connection([root]))]))], fetch=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(value[0]["comment_id"], 101)

    def test_complete_dry_run(self):
        result, calls, _ = self.run_helper([step(outer([thread(), thread(202)])), step(live()), step(live(202))], replies=[reply(), reply(202)], snapshot=[reviewed(), reviewed(202)], dry=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would_post=2", result.stdout)
        self.assertFalse(any(c["kind"] == "post" for c in calls))

    def test_incomplete_inventory_blocks(self):
        result, calls, _ = self.run_helper([step(outer([thread(), thread(202)]))], dry=True)
        self.assert_blocked(result, calls)

    def test_invalid_and_duplicate_inputs_never_post(self):
        bad = [reply(body=""), reply(body=42), {**reply(), "comment_id": -1}, {**reply(), "comment_id": 1.5}, {**reply(), "thread_id": ""}]
        raw_values = [json.dumps([item]) for item in bad] + [json.dumps([reply(), reply()]), json.dumps([reply()]) * 2,
                      json.dumps([reply(), {**reply(), "thread_id": "T202"}])]
        for raw in raw_values:
            with self.subTest(raw=raw):
                result, calls, _ = self.run_helper([step(outer([thread()])), step(live())], raw=raw)
                self.assert_blocked(result, calls)

    def test_wrong_identity_and_graphql_errors_block(self):
        bad = []
        for key in ("repo", "pr", "root"):
            response = live()
            if key == "repo": response["data"]["node"]["pullRequest"]["repository"]["name"] = "Other"
            if key == "pr": response["data"]["node"]["pullRequest"]["number"] = 8
            if key == "root": response["data"]["node"]["comments"]["nodes"][0]["databaseId"] = 303
            bad.append(response)
        bad += [{"errors": [{"message": "denied"}], **live()}, {"data": {"node": None}}]
        for response in bad:
            with self.subTest(response=response):
                result, calls, _ = self.run_helper([step(outer([thread()])), step(response)])
                self.assert_blocked(result, calls)

    def test_surplus_resolved_thread_is_validated_and_skipped(self):
        result, _, _ = self.run_helper([step(outer([thread()])), step(live()), step(live(202, resolved=True))], replies=[reply(), reply(202)], snapshot=[reviewed(), reviewed(202)], dry=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would_post=1 skipped=1", result.stdout)

    def test_stale_root_or_new_reply_blocks(self):
        variants = [connection([comment(body="Updated concern")]), connection([comment(), comment(102, "New concern", True)])]
        for comments in variants:
            with self.subTest(comments=comments):
                result, calls, _ = self.run_helper([step(outer([thread()])), step(live(comments=comments))])
                self.assert_blocked(result, calls)

    def test_stable_paginated_thread_can_post(self):
        previous = reviewed()
        previous["replies"] = [{"comment_id": 102, "author": "reviewer", "body": "Context", "created_at": "2026-10-04T00:00:00Z"}]
        first = connection([comment()], True, "next")
        result, calls, _ = self.run_helper([step(outer([thread()])), step(live(comments=first)),
            step({"data": {"node": {"comments": connection([comment(102, "Context", True)])}}}), step({}, kind="post")], snapshot=[previous])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1]["payload"], {"body": "Fixed and verified."})

    def test_large_multiline_body_preserved_in_json_file(self):
        body = "literal `code` $HOME\n" * 9000 + "\n\n"
        result, calls, _ = self.run_helper([step(outer([thread()])), step(live()), step({}, kind="post")], replies=[reply(body=body)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1]["payload"]["body"], body)
        self.assertNotIn(body, calls[-1]["args"])

    def test_post_or_lookup_failure_aborts_remaining_batch(self):
        for failure in ("post", "lookup"):
            steps = [step(outer([thread(), thread(202)]))]
            steps += [step(live()), step(fail=True, kind="post")] if failure == "post" else [step(fail=True)]
            result, calls, _ = self.run_helper(steps, replies=[reply(), reply(202)], snapshot=[reviewed(), reviewed(202)])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(len(calls), len(steps))
            self.assertIn("posted=0", result.stdout)
            self.assertIn("failed=1", result.stdout)

    def test_partial_success_counts_without_retry(self):
        result, calls, _ = self.run_helper([step(outer([thread(), thread(202)])), step(live()), step({}, kind="post"), step(live(202)), step(fail=True, kind="post")], replies=[reply(), reply(202)], snapshot=[reviewed(), reviewed(202)])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(c["kind"] == "post" for c in calls), 2)
        self.assertIn("posted=1", result.stdout)
        self.assertIn("failed=1", result.stdout)

    def test_caller_file_edits_cannot_change_the_posted_snapshot(self):
        changed = {**step(outer([thread()])), "mutations": {
            "replies.json": [reply(body="Replaced after validation")],
            "reviewed.json": [{**reviewed(), "body": "Replaced concern"}]}}
        result, calls, _ = self.run_helper([changed, step(live()), step({}, kind="post")])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1]["payload"], {"body": "Fixed and verified."})

    def test_edited_or_deleted_existing_reply_blocks(self):
        previous = {**reviewed(), "replies": [{"comment_id": 102, "author": "reviewer", "body": "Original reply"}]}
        for comments in (connection([comment()]), connection([comment(), comment(102, "Edited reply", True)])):
            result, calls, _ = self.run_helper([step(outer([thread()])), step(live(comments=comments))], snapshot=[previous])
            self.assert_blocked(result, calls)

    def test_incomplete_reviewed_snapshot_blocks(self):
        for snapshot in ([], [{**reviewed(), "replies_truncated": True}], [reviewed(), reviewed()]):
            result, calls, _ = self.run_helper([step(outer([thread()])), step(live())], snapshot=snapshot)
            self.assert_blocked(result, calls)


if __name__ == "__main__":
    unittest.main()
