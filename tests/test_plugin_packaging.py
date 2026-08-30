#!/usr/bin/env python3
"""Regression tests for portable plugin packaging and marketplace adapters."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PLUGIN_NAMES = {
    path.stem for path in (ROOT / "packaging").glob("*.json")
}


def load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PluginPackagingTests(unittest.TestCase):
    def test_generator_discovers_every_plugin_config(self) -> None:
        generator = load_script("generate-plugin-packages")

        configs = generator.load_package_configs()

        self.assertEqual({config["name"] for config in configs}, EXPECTED_PLUGIN_NAMES)
        self.assertIn("g0ld2k-apple-design", EXPECTED_PLUGIN_NAMES)

    def test_shared_conventions_sync_discovers_every_plugin_config(self) -> None:
        sync = load_script("sync-shared-conventions")

        configs = sync.load_package_configs()

        self.assertEqual({config["name"] for config in configs}, EXPECTED_PLUGIN_NAMES)

    def test_generated_manifests_use_the_portable_agent_plugins_contract(self) -> None:
        generator = load_script("generate-plugin-packages")

        for config in generator.load_package_configs():
            manifest = json.loads(
                (ROOT / "plugins" / config["name"] / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                manifest.get("$schema"),
                "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            )
            self.assertNotIn("skills", manifest)
            self.assertNotIn("category", manifest)
            self.assertFalse(
                (ROOT / "plugins" / config["name"] / ".claude-plugin").exists()
            )
            self.assertFalse(
                (ROOT / "plugins" / config["name"] / ".codex-plugin").exists()
            )

    def test_catalogs_publish_only_componentful_plugins_and_share_sources(self) -> None:
        codex = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        copilot = json.loads(
            (ROOT / ".github/plugin/marketplace.json").read_text(encoding="utf-8")
        )

        self.assertEqual(codex["interface"]["displayName"], "g0ld2k skills")
        self.assertEqual(
            [entry["name"] for entry in codex["plugins"]], ["g0ld2k-skills"]
        )
        self.assertEqual(
            [entry["name"] for entry in copilot["plugins"]], ["g0ld2k-skills"]
        )
        self.assertEqual(
            codex["plugins"][0]["source"]["path"], copilot["plugins"][0]["source"]
        )
        self.assertFalse((ROOT / ".claude-plugin/marketplace.json").exists())

    def test_validator_rejects_a_manifest_with_unknown_fields(self) -> None:
        validator = load_script("validate-skills-repo")
        errors: list[str] = []

        validator.validate_portable_manifest(
            {"$schema": validator.PLUGIN_SCHEMA_URL, "name": "example", "skills": "./skills/"},
            Path("plugins/example/plugin.json"),
            errors,
        )

        self.assertEqual(
            errors,
            ["plugins/example/plugin.json: schema validation failed: additional property 'skills'"],
        )

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

    def test_validator_accepts_empty_plugin_without_publishing_it(self) -> None:
        validator = load_script("validate-skills-repo")
        errors: list[str] = []

        configs = validator.load_package_configs(errors)
        validator.validate_packaging(validator.validate_skills(errors), errors, configs)

        self.assertEqual(errors, [])
        empty_skills_dir = ROOT / "plugins" / "g0ld2k-apple-design" / "skills"
        self.assertTrue(empty_skills_dir.is_dir())
        self.assertTrue((empty_skills_dir / ".gitkeep").is_file())
        self.assertEqual(
            [path for path in empty_skills_dir.iterdir() if path.is_dir()],
            [],
        )

        codex = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        self.assertNotIn(
            "g0ld2k-apple-design", [entry["name"] for entry in codex["plugins"]]
        )


if __name__ == "__main__":
    unittest.main()
