#!/usr/bin/env python3
"""Regression tests for the Agent Plugins v1 repository shape."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "plugin.json"
SCHEMA = ROOT / "schemas" / "agent-plugins" / "1.0.0" / "plugin.schema.json"
SCHEMA_URL = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"


def load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    return module


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PluginManifestTests(unittest.TestCase):
    def test_manifest_declares_the_pinned_schema(self) -> None:
        manifest = read_json(MANIFEST)

        self.assertEqual(manifest["$schema"], SCHEMA_URL)
        self.assertEqual(manifest["name"], "g0ld2k-skills")

    def test_manifest_uses_only_schema_defined_fields(self) -> None:
        manifest = read_json(MANIFEST)
        allowed = set(read_json(SCHEMA)["properties"])

        self.assertEqual(set(manifest) - allowed, set())

    def test_validator_accepts_the_manifest(self) -> None:
        validator = load_script("validate-skills-repo")
        errors: list[str] = []

        validator.validate_plugin_manifest(errors)

        self.assertEqual(errors, [])

    def test_validator_rejects_a_field_the_schema_forbids(self) -> None:
        errors = self._errors_for({"category": "Developer Tools"})

        self.assertTrue(any("category" in error for error in errors), errors)

    def test_validator_enforces_types_items_and_nested_objects(self) -> None:
        """The pinned schema constrains more than the top-level field set."""
        for mutation, expected in (
            ({"version": []}, "version"),
            ({"keywords": "not-an-array"}, "keywords"),
            ({"keywords": ["ok", 5]}, "keywords[1]"),
            ({"author": {"bogus": 1}}, "author"),
            ({"extensions": "str"}, "extensions"),
            ({"name": "a--b"}, "name"),
            ({"name": "a" * 65}, "name"),
        ):
            with self.subTest(mutation=mutation):
                errors = self._errors_for(mutation)
                self.assertTrue(
                    any(expected in error for error in errors),
                    f"{mutation} produced {errors}",
                )

    def _errors_for(self, mutation: dict) -> list[str]:
        validator = load_script("validate-skills-repo")
        errors: list[str] = []
        original = MANIFEST.read_text(encoding="utf-8")
        manifest = read_json(MANIFEST)
        manifest.update(mutation)
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        try:
            validator.validate_plugin_manifest(errors)
        finally:
            MANIFEST.write_text(original, encoding="utf-8")
        return errors


class RepositoryShapeTests(unittest.TestCase):
    def test_skills_are_discoverable_at_the_plugin_root(self) -> None:
        skill_dirs = [
            path for path in (ROOT / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        ]

        self.assertGreater(len(skill_dirs), 0)

    def test_generated_packaging_layer_is_absent(self) -> None:
        for stale in ("plugins", "packaging", ".claude-plugin"):
            self.assertFalse((ROOT / stale).exists(), f"{stale}/ must not exist")
        self.assertFalse((ROOT / "scripts" / "generate-plugin-packages.py").exists())

    def test_marketplace_adapters_point_at_the_repository_root(self) -> None:
        codex = read_json(ROOT / ".agents" / "plugins" / "marketplace.json")
        copilot = read_json(ROOT / ".github" / "plugin" / "marketplace.json")

        self.assertEqual([p["name"] for p in codex["plugins"]], ["g0ld2k-skills"])
        self.assertEqual(codex["plugins"][0]["source"]["path"], ".")
        self.assertEqual([p["name"] for p in copilot["plugins"]], ["g0ld2k-skills"])
        self.assertEqual(copilot["plugins"][0]["source"], ".")

    def test_validator_catches_adapter_drift_from_the_root_manifest(self) -> None:
        """The generated packaging layer used to guarantee this by construction."""
        validator = load_script("validate-skills-repo")
        adapter = ROOT / ".github" / "plugin" / "marketplace.json"
        original = adapter.read_text(encoding="utf-8")
        for mutation, expected in (
            ({"version": "9.9.9"}, "version must match"),
            ({"description": "drifted"}, "description must match"),
            ({"source": "./plugins/g0ld2k-skills"}, "source must point at"),
        ):
            with self.subTest(mutation=mutation):
                data = json.loads(original)
                data["plugins"][0].update(mutation)
                adapter.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                errors: list[str] = []
                try:
                    validator.validate_plugin_manifest(errors)
                finally:
                    adapter.write_text(original, encoding="utf-8")
                self.assertTrue(
                    any(expected in error for error in errors),
                    f"{mutation} produced {errors}",
                )


class ExplicitOnlyInvocationTests(unittest.TestCase):
    """Both install paths need their own guard; neither client reads the other's."""

    EXPLICIT_ONLY = ("integration-branch-orchestrator", "work-request-orchestration")

    def test_claude_guard_present_in_frontmatter(self) -> None:
        for name in self.EXPLICIT_ONLY:
            with self.subTest(skill=name):
                text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("disable-model-invocation: true", text)

    def test_codex_guard_present_in_openai_yaml(self) -> None:
        for name in self.EXPLICIT_ONLY:
            with self.subTest(skill=name):
                text = (ROOT / "skills" / name / "agents" / "openai.yaml").read_text(encoding="utf-8")
                self.assertIn("allow_implicit_invocation: false", text)

    def test_validator_requires_the_claude_guard(self) -> None:
        validator = load_script("validate-skills-repo")
        skill = ROOT / "skills" / self.EXPLICIT_ONLY[0] / "SKILL.md"
        original = skill.read_text(encoding="utf-8")
        skill.write_text(original.replace("disable-model-invocation: true\n", ""), encoding="utf-8")
        errors: list[str] = []
        try:
            validator.validate_skills(errors)
        finally:
            skill.write_text(original, encoding="utf-8")

        self.assertTrue(any("disable-model-invocation" in e for e in errors), errors)


class SharedConventionsTests(unittest.TestCase):
    def test_consumers_come_from_skill_instructions(self) -> None:
        shared = load_script("shared_conventions")

        consumers = shared.consumer_names(ROOT / "skills")

        self.assertIn("commit-message", consumers)
        self.assertNotIn("catch-me-up", consumers)
        for name in consumers:
            skill = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("references/conventions.md", skill)


if __name__ == "__main__":
    unittest.main()
