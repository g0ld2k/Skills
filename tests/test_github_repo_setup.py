#!/usr/bin/env python3
"""Regression tests for github-repo-setup's apply script, run against a stub gh."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "github-repo-setup" / "scripts" / "apply-github-setup.sh"
REPO = "owner/app"
CI_CHECK = "App | PR - Fast Gate"

# Answers GET requests from $STUB_FIXTURES (endpoint -> JSON) and logs every call
# to $STUB_LOG. A missing endpoint behaves like a 404.
STUB_GH = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, subprocess, sys

    args = sys.argv[1:]
    fixtures = json.load(open(os.environ["STUB_FIXTURES"]))
    entry = {"args": args}
    if args[0] == "api":
        method, jq, endpoint, i = "GET", None, None, 1
        while i < len(args):
            if args[i] == "--method":
                method = args[i + 1]; i += 2
            elif args[i] == "--jq":
                jq = args[i + 1]; i += 2
            elif args[i] == "--input":
                entry["input"] = json.loads(sys.stdin.read()); i += 2
            elif args[i].startswith("--"):
                i += 1
            else:
                endpoint = args[i]; i += 1
        entry.update(method=method, endpoint=endpoint)
        with open(os.environ["STUB_LOG"], "a") as log:
            log.write(json.dumps(entry) + "\\n")
        if method != "GET":
            sys.exit(0)
        if endpoint not in fixtures:
            sys.exit(1)
        body = json.dumps(fixtures[endpoint])
        if jq:
            body = subprocess.run(["jq", "-r", jq], input=body, text=True,
                                  capture_output=True, check=True).stdout
        sys.stdout.write(body)
    else:
        with open(os.environ["STUB_LOG"], "a") as log:
            log.write(json.dumps(entry) + "\\n")
    """
)

GHA = 15368
XCODE_CLOUD = 117084


def ruleset(rules: list[dict], include: str = "~DEFAULT_BRANCH", exclude: tuple = ()) -> dict:
    return {
        "id": 7, "target": "branch", "source_type": "Repository", "enforcement": "active",
        "conditions": {"ref_name": {"include": [include], "exclude": list(exclude)}}, "rules": rules,
    }


def configured_rules() -> list[dict]:
    return [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {"type": "pull_request", "parameters": {
            "required_approving_review_count": 0, "allowed_merge_methods": ["squash"],
            "require_extra_approval_for_unattributed_changes": True}},
        {"type": "required_linear_history"},
        {"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": False,
            "required_status_checks": [
                {"context": CI_CHECK, "integration_id": XCODE_CLOUD},
                {"context": "Label gate", "integration_id": GHA},
                {"context": "PR title", "integration_id": GHA}]}},
    ]


def configured_repo() -> dict:
    """GET responses for a repository that already has the full setup."""
    return {
        f"repos/{REPO}": {
            "default_branch": "main", "allow_squash_merge": True, "allow_merge_commit": False,
            "allow_rebase_merge": False, "squash_merge_commit_title": "PR_TITLE",
            "squash_merge_commit_message": "PR_BODY", "delete_branch_on_merge": True,
            "allow_update_branch": True, "allow_auto_merge": True, "has_wiki": False,
            "has_projects": False, "has_issues": True},
        f"repos/{REPO}/actions/permissions": {
            "enabled": True, "allowed_actions": "selected", "sha_pinning_required": True,
            "selected_actions_url": "https://example.invalid"},
        f"repos/{REPO}/actions/permissions/selected-actions": {
            "github_owned_allowed": True, "verified_allowed": False, "patterns_allowed": []},
        f"repos/{REPO}/actions/permissions/workflow": {
            "default_workflow_permissions": "read", "can_approve_pull_request_reviews": False},
        f"repos/{REPO}/labels/needs-human-verification": {"name": "needs-human-verification"},
        f"repos/{REPO}/contents/.github/workflows/pr-label-gate.yml?ref=main": {},
        f"repos/{REPO}/contents/.github/workflows/pr-title.yml?ref=main": {},
        f"repos/{REPO}/rulesets": [{"id": 7, "target": "branch", "source_type": "Repository"}],
        f"repos/{REPO}/rulesets/7": ruleset(configured_rules()),
    }


class ApplyGithubSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp = Path(self.tmp.name)
        stub = tmp / "bin" / "gh"
        stub.parent.mkdir()
        stub.write_text(STUB_GH, encoding="utf-8")
        stub.chmod(0o755)
        self.log = tmp / "calls.jsonl"
        self.fixtures = tmp / "fixtures.json"
        self.env = {**os.environ, "PATH": f"{stub.parent}{os.pathsep}{os.environ['PATH']}",
                    "STUB_LOG": str(self.log), "STUB_FIXTURES": str(self.fixtures)}

    def run_script(self, fixtures: dict, *args: str) -> subprocess.CompletedProcess:
        self.fixtures.write_text(json.dumps(fixtures), encoding="utf-8")
        self.log.write_text("", encoding="utf-8")
        return subprocess.run([str(SCRIPT), *args, "--repo", REPO], env=self.env,
                              capture_output=True, text=True)

    def writes(self) -> list[dict]:
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        return [c for c in calls if c.get("method", "WRITE") != "GET"]

    def test_settings_applies_merge_and_actions_policy(self) -> None:
        result = self.run_script(configured_repo(), "settings")

        self.assertEqual(result.returncode, 0, result.stderr)
        writes = {c.get("endpoint", "label"): c for c in self.writes()}
        repo = writes[f"repos/{REPO}"]
        self.assertEqual(repo["method"], "PATCH")
        self.assertEqual(repo["input"]["squash_merge_commit_message"], "PR_BODY")
        self.assertFalse(repo["input"]["allow_merge_commit"])
        self.assertTrue(writes[f"repos/{REPO}/actions/permissions"]["input"]["sha_pinning_required"])
        self.assertEqual(
            writes[f"repos/{REPO}/actions/permissions/workflow"]["input"]["default_workflow_permissions"],
            "read")
        self.assertIn("needs-human-verification", writes["label"]["args"])

    def test_dry_run_writes_nothing(self) -> None:
        for phase in (["settings"], ["ruleset", "--ci-check", CI_CHECK]):
            with self.subTest(phase=phase[0]):
                result = self.run_script(configured_repo(), *phase, "--dry-run")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("would ", result.stdout)
                self.assertEqual(self.writes(), [])

    def test_ruleset_waits_for_the_workflows_to_merge(self) -> None:
        fixtures = configured_repo()
        del fixtures[f"repos/{REPO}/contents/.github/workflows/pr-title.yml?ref=main"]

        result = self.run_script(fixtures, "ruleset", "--ci-check", CI_CHECK)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pr-title.yml", result.stderr)
        self.assertEqual(self.writes(), [])

    def test_ruleset_updates_the_existing_ruleset_and_keeps_unmanaged_rules(self) -> None:
        fixtures = configured_repo()
        fixtures[f"repos/{REPO}/rulesets/7"] = ruleset(
            [{"type": "required_signatures"}, {"type": "deletion"},
             {"type": "pull_request", "parameters": {"required_approving_review_count": 1}}],
            include="refs/heads/main")

        result = self.run_script(fixtures, "ruleset", "--ci-check", CI_CHECK)

        self.assertEqual(result.returncode, 0, result.stderr)
        [write] = self.writes()
        self.assertEqual((write["method"], write["endpoint"]), ("PUT", f"repos/{REPO}/rulesets/7"))
        rules = write["input"]["rules"]
        self.assertEqual([r["type"] for r in rules].count("deletion"), 1)
        self.assertIn("required_signatures", [r["type"] for r in rules])
        pull_request = next(r for r in rules if r["type"] == "pull_request")
        self.assertEqual(pull_request["parameters"]["required_approving_review_count"], 0)
        checks = next(r for r in rules if r["type"] == "required_status_checks")
        self.assertIn({"context": CI_CHECK, "integration_id": XCODE_CLOUD},
                      checks["parameters"]["required_status_checks"])
        self.assertFalse(checks["parameters"]["strict_required_status_checks_policy"])

    def test_ruleset_is_created_when_none_targets_the_default_branch(self) -> None:
        fixtures = configured_repo()
        fixtures[f"repos/{REPO}/rulesets/7"] = ruleset([], include="refs/heads/release")

        result = self.run_script(fixtures, "ruleset", "--ci-check", CI_CHECK)

        self.assertEqual(result.returncode, 0, result.stderr)
        [write] = self.writes()
        self.assertEqual((write["method"], write["endpoint"]), ("POST", f"repos/{REPO}/rulesets"))
        self.assertEqual(write["input"]["conditions"]["ref_name"]["include"], ["~DEFAULT_BRANCH"])

    def test_ruleset_skips_a_ruleset_that_excludes_the_default_branch(self) -> None:
        fixtures = configured_repo()
        fixtures[f"repos/{REPO}/rulesets/7"] = ruleset(
            configured_rules(), include="~ALL", exclude=("refs/heads/main",))

        result = self.run_script(fixtures, "verify", "--ci-check", CI_CHECK)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("no ruleset targets the default branch", result.stdout)

        result = self.run_script(fixtures, "ruleset", "--ci-check", CI_CHECK)
        self.assertEqual(result.returncode, 0, result.stderr)
        [write] = self.writes()
        self.assertEqual((write["method"], write["endpoint"]), ("POST", f"repos/{REPO}/rulesets"))

    def test_ruleset_stops_when_the_lookup_fails(self) -> None:
        for missing in (f"repos/{REPO}/rulesets", f"repos/{REPO}/rulesets/7"):
            with self.subTest(missing=missing):
                fixtures = configured_repo()
                del fixtures[missing]

                result = self.run_script(fixtures, "ruleset", "--ci-check", CI_CHECK)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.writes(), [])

    def test_verify_passes_on_the_configured_repo_and_reports_drift(self) -> None:
        result = self.run_script(configured_repo(), "verify", "--ci-check", CI_CHECK)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("drift", result.stdout)

        fixtures = configured_repo()
        fixtures[f"repos/{REPO}"]["allow_merge_commit"] = True
        del fixtures[f"repos/{REPO}/labels/needs-human-verification"]
        result = self.run_script(fixtures, "verify", "--ci-check", CI_CHECK)
        self.assertEqual(result.returncode, 1)
        self.assertIn("drift  repository settings", result.stdout)
        self.assertIn("drift  label", result.stdout)
        self.assertEqual(self.writes(), [])


if __name__ == "__main__":
    unittest.main()
