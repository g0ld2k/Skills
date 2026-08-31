#!/usr/bin/env python3
"""Regression tests for the root Agent Plugin and marketplace adapters."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "g0ld2k-skills"


def load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class RootPluginTests(unittest.TestCase):
    def test_python_cache_artifacts_do_not_dirty_repository(self) -> None:
        cache_dir = ROOT / "scripts" / "__pycache__"
        cache_dir_preexisted = cache_dir.exists()
        cache_dir.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=cache_dir, prefix="ci-regression-", suffix=".pyc", delete=False
        ) as handle:
            handle.write(b"test artifact")
            artifact = Path(handle.name)
        try:
            result = subprocess.run(
                [
                    "git",
                    "status",
                    "--porcelain",
                    "--untracked-files=all",
                    "--",
                    str(artifact.relative_to(ROOT)),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            artifact.unlink()
            if not cache_dir_preexisted:
                try:
                    cache_dir.rmdir()
                except OSError:
                    pass

        self.assertEqual(result.stdout, "")

    def test_root_manifest_uses_the_portable_agent_plugins_contract(self) -> None:
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))

        self.assertEqual(
            manifest.get("$schema"),
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertEqual(manifest.get("name"), PLUGIN_NAME)
        self.assertNotIn("skills", manifest)
        self.assertNotIn("category", manifest)
        self.assertFalse((ROOT / ".claude-plugin/plugin.json").exists())
        self.assertFalse((ROOT / ".codex-plugin/plugin.json").exists())

    def test_repository_has_one_canonical_skill_tree(self) -> None:
        skill_names = sorted(
            path.name for path in (ROOT / "skills").iterdir() if path.is_dir()
        )

        self.assertTrue(skill_names)
        self.assertFalse((ROOT / "plugins").exists())
        self.assertFalse((ROOT / "packaging").exists())
        self.assertFalse((ROOT / "scripts/generate-plugin-packages.py").exists())

    def test_catalogs_publish_the_root_plugin(self) -> None:
        codex = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        copilot = json.loads(
            (ROOT / ".github/plugin/marketplace.json").read_text(encoding="utf-8")
        )

        self.assertEqual(codex["interface"]["displayName"], "g0ld2k skills")
        self.assertEqual([entry["name"] for entry in codex["plugins"]], [PLUGIN_NAME])
        self.assertEqual(
            [entry["name"] for entry in copilot["plugins"]], [PLUGIN_NAME]
        )
        self.assertEqual(codex["plugins"][0]["source"]["path"], ".")
        self.assertEqual(copilot["plugins"][0]["source"], ".")
        self.assertFalse((ROOT / ".claude-plugin/marketplace.json").exists())

    def test_shared_convention_consumers_come_from_skill_instructions(self) -> None:
        sync = load_script("sync-shared-conventions")

        self.assertEqual(
            sync.consumer_names(sync.SKILLS_DIR),
            [
                "commit-message",
                "integration-branch-orchestrator",
                "pr-closeout-loop",
                "pr-comment-review",
                "pr-generator",
                "simplify",
                "work-request-orchestration",
            ],
        )

    def test_validator_accepts_the_root_plugin(self) -> None:
        validator = load_script("validate-skills-repo")
        errors: list[str] = []

        canonical_names = validator.validate_skills(errors)
        validator.validate_root_plugin(canonical_names, errors)
        validator.validate_shared_conventions(errors)

        self.assertEqual(errors, [])

    def test_validator_rejects_a_manifest_with_unknown_fields(self) -> None:
        validator = load_script("validate-skills-repo")
        errors: list[str] = []

        validator.validate_portable_manifest(
            {
                "$schema": validator.PLUGIN_SCHEMA_URL,
                "name": "example",
                "skills": "./skills/",
            },
            Path("plugin.json"),
            errors,
        )

        self.assertEqual(
            errors,
            ["plugin.json: schema validation failed: additional property 'skills'"],
        )

    def test_validator_rejects_a_non_object_json_root(self) -> None:
        validator = load_script("validate-skills-repo")
        original_root = validator.ROOT

        with tempfile.TemporaryDirectory(prefix="plugin-validation-") as temp:
            validator.ROOT = Path(temp)
            manifest_path = validator.ROOT / "plugin.json"
            manifest_path.write_text("[]\n", encoding="utf-8")
            errors: list[str] = []
            try:
                manifest = validator.load_json(manifest_path, errors)
            finally:
                validator.ROOT = original_root

        self.assertIsNone(manifest)
        self.assertEqual(errors, ["plugin.json: JSON root must be an object"])

    def test_explicit_only_behavior_is_client_metadata_not_portable_frontmatter(self) -> None:
        validator = load_script("validate-skills-repo")

        for name in validator.EXPLICIT_ONLY_SKILLS:
            frontmatter, parse_error = validator.parse_frontmatter(
                ROOT / "skills" / name / "SKILL.md"
            )

            self.assertIsNone(parse_error)
            self.assertNotIn("disable-model-invocation", frontmatter)
            _, policy, openai_error = validator.parse_openai_yaml(
                ROOT / "skills" / name / "agents/openai.yaml"
            )
            self.assertIsNone(openai_error)
            self.assertIs(policy.get("allow_implicit_invocation"), False)


if __name__ == "__main__":
    unittest.main()
