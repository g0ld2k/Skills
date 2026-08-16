#!/usr/bin/env python3
"""Behavior tests for the guarded Apple design scenario drift check."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-skills-repo.py"
RENDERER = ROOT / "scripts" / "render-validation-scenarios.py"


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_skills_repo", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load repository validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_temp_dir() -> Path:
    template = str(Path(os.environ.get("TMPDIR", "/tmp")) / "apple-design-validator-tests.XXXXXX")
    result = subprocess.run(
        ["mktemp", "-d", template],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def minimal_case() -> dict[str, object]:
    return {
        "id": "discovery-01",
        "kind": "discovery",
        "split": "calibration",
        "title": "Example",
        "tags": ["positive"],
        "setup": "The advisor is discoverable.",
        "prompt": "Help choose an iPad container.",
        "capabilities": [],
        "fixture": None,
        "expected": {
            "route": "invoke",
            "references": ["advise:container"],
            "assertions": ["Invoke for the unresolved design choice."],
            "forbidden": [],
        },
    }


class ValidateAppleDesignScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = make_temp_dir()
        self.module = load_validator()
        self.module.ROOT = self.temp_dir
        self.module.SKILLS_DIR = self.temp_dir / "skills"
        self.module.APPLE_DESIGN_CASES = (
            self.temp_dir / "evals" / "apple-platform-design" / "cases.jsonl"
        )
        self.module.APPLE_DESIGN_RENDERER = RENDERER
        self.module.APPLE_DESIGN_PREVIEW = (
            self.temp_dir
            / "evals"
            / "apple-platform-design"
            / "validation-scenarios.preview.md"
        )
        self.module.APPLE_DESIGN_SCENARIOS = (
            self.temp_dir
            / "skills"
            / "apple-platform-design"
            / "references"
            / "validation-scenarios.md"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def write_valid_wave1_artifacts(self) -> None:
        self.module.APPLE_DESIGN_CASES.parent.mkdir(parents=True, exist_ok=True)
        self.module.APPLE_DESIGN_CASES.write_text(
            json.dumps(minimal_case()) + "\n", encoding="utf-8"
        )
        result = subprocess.run(
            [
                "python3",
                str(RENDERER),
                "--cases",
                str(self.module.APPLE_DESIGN_CASES),
                "--output",
                str(self.module.APPLE_DESIGN_PREVIEW),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_skill_target_no_ops_after_wave1_validation(self) -> None:
        self.write_valid_wave1_artifacts()
        errors: list[str] = []

        self.module.validate_apple_platform_design_scenarios(errors)

        self.assertEqual(errors, [])

    def test_reports_malformed_corpus_before_skill_exists(self) -> None:
        self.module.APPLE_DESIGN_CASES.parent.mkdir(parents=True, exist_ok=True)
        self.module.APPLE_DESIGN_CASES.write_text("{not-json}\n", encoding="utf-8")
        self.module.APPLE_DESIGN_PREVIEW.write_text("stale\n", encoding="utf-8")
        errors: list[str] = []

        self.module.validate_apple_platform_design_scenarios(errors)

        self.assertEqual(len(errors), 1)
        self.assertIn("could not verify generated scenarios", errors[0])
        self.assertIn("invalid JSON", errors[0])

    def test_reports_stale_preview_before_skill_exists(self) -> None:
        self.module.APPLE_DESIGN_CASES.parent.mkdir(parents=True, exist_ok=True)
        self.module.APPLE_DESIGN_CASES.write_text(
            json.dumps(minimal_case()) + "\n", encoding="utf-8"
        )
        self.module.APPLE_DESIGN_PREVIEW.write_text("stale\n", encoding="utf-8")
        errors: list[str] = []

        self.module.validate_apple_platform_design_scenarios(errors)

        self.assertEqual(
            errors,
            [
                "evals/apple-platform-design/validation-scenarios.preview.md: "
                "stale; run python3 scripts/render-validation-scenarios.py"
            ],
        )

    def test_reports_drift_when_skill_target_is_stale(self) -> None:
        self.write_valid_wave1_artifacts()
        self.module.APPLE_DESIGN_SCENARIOS.parent.mkdir(parents=True)
        self.module.APPLE_DESIGN_SCENARIOS.write_text("stale\n", encoding="utf-8")
        errors: list[str] = []

        self.module.validate_apple_platform_design_scenarios(errors)

        self.assertEqual(
            errors,
            [
                "skills/apple-platform-design/references/validation-scenarios.md: "
                "stale; run python3 scripts/render-validation-scenarios.py "
                "--scope calibration "
                "--output skills/apple-platform-design/references/validation-scenarios.md"
            ],
        )


if __name__ == "__main__":
    unittest.main()
