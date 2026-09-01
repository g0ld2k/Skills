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
        validator = load_script("validate-skills-repo")
        errors: list[str] = []
        original = MANIFEST.read_text(encoding="utf-8")
        manifest = read_json(MANIFEST)
        manifest["category"] = "Developer Tools"
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        try:
            validator.validate_plugin_manifest(errors)
        finally:
            MANIFEST.write_text(original, encoding="utf-8")

        self.assertTrue(any("category" in error for error in errors), errors)


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
