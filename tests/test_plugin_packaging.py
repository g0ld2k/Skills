#!/usr/bin/env python3
"""Regression tests for multi-plugin package discovery and validation."""

from __future__ import annotations

import importlib.util
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

    def test_validator_accepts_empty_plugin(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
