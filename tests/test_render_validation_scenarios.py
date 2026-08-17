#!/usr/bin/env python3
"""Behavior tests for the validation-scenario renderer."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import struct
import subprocess
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render-validation-scenarios.py"
CONDITIONS = ROOT / "evals" / "apple-platform-design" / "conditions.json"
SYNTHETIC_VISUAL_FIXTURE = (
    ROOT
    / "evals"
    / "apple-platform-design"
    / "fixtures"
    / "synthetic-visual-injection.png"
)


def load_renderer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("render_validation_scenarios", RENDERER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load scenario renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_temp_dir() -> Path:
    template = str(
        Path(os.environ.get("TMPDIR") or "/tmp")
        / "apple-design-render-tests.XXXXXX"
    )
    result = subprocess.run(
        ["mktemp", "-d", template],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def case(case_id: str, title: str) -> dict[str, object]:
    return {
        "id": case_id,
        "kind": "discovery",
        "split": "calibration",
        "title": title,
        "tags": ["positive", "bounded-advice"],
        "setup": "No artifacts are supplied.",
        "prompt": "Should this recurring settings destination use a push or a sheet?",
        "capabilities": ["fetch"],
        "fixture": None,
        "expected": {
            "route": "invoke",
            "references": ["advise:container"],
            "assertions": [
                "Resolve the material container decision and state a reversal condition.",
                "Verify or remove each Apple-attributed proposition.",
            ],
            "forbidden": ["Stop after emitting a handoff artifact."],
        },
    }


class RenderValidationScenariosTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = make_temp_dir()
        self.cases_path = self.temp_dir / "cases.jsonl"
        self.output_path = self.temp_dir / "validation-scenarios.md"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def run_renderer(self, *extra_args: str) -> subprocess.CompletedProcess[str]:
        arguments = [
            "python3",
            str(RENDERER),
            "--cases",
            str(self.cases_path),
        ]
        if extra_args:
            arguments.extend(extra_args)
        else:
            arguments.extend(["--output", str(self.output_path)])
        return subprocess.run(
            arguments,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def write_cases(self, cases: list[dict[str, object]]) -> None:
        self.cases_path.write_text(
            "".join(json.dumps(item) + "\n" for item in cases),
            encoding="utf-8",
        )

    def test_renders_cases_in_stable_id_order(self) -> None:
        self.write_cases([case("discovery-02", "Second"), case("discovery-01", "First")])

        result = self.run_renderer()

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = self.output_path.read_text(encoding="utf-8")
        self.assertTrue(rendered.startswith("<!-- GENERATED from evals/apple-platform-design/cases.jsonl"))
        self.assertLess(rendered.index("## Scenario discovery-01"), rendered.index("## Scenario discovery-02"))
        self.assertIn("**Route:** `invoke`", rendered)
        self.assertIn("### Pass criteria", rendered)
        self.assertIn("### Forbidden behavior", rendered)
        self.assertTrue(rendered.endswith("\n"))

    def test_rejects_duplicate_case_ids_without_writing_output(self) -> None:
        self.write_cases([case("discovery-01", "First"), case("discovery-01", "Duplicate")])

        result = self.run_renderer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate case id: discovery-01", result.stderr)
        self.assertFalse(self.output_path.exists())

    def test_check_reports_drift_without_rewriting_target(self) -> None:
        self.write_cases([case("discovery-01", "First")])
        self.output_path.write_text("stale\n", encoding="utf-8")

        result = self.run_renderer("--check", str(self.output_path))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale generated scenarios", result.stderr)
        self.assertEqual(self.output_path.read_text(encoding="utf-8"), "stale\n")

    def test_rejects_missing_repository_fixture(self) -> None:
        item = case("evidence-01", "Missing fixture")
        item["fixture"] = "evals/apple-platform-design/fixtures/does-not-exist.md"
        item["fixture_media"] = "text"
        self.write_cases([item])

        result = self.run_renderer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture does not exist", result.stderr)
        self.assertFalse(self.output_path.exists())

    def test_rejects_fixture_media_that_does_not_match_file_type(self) -> None:
        item = case("evidence-01", "Wrong media")
        item["fixture"] = (
            "evals/apple-platform-design/fixtures/synthetic-design-guidance.md"
        )
        item["fixture_media"] = "image"
        self.write_cases([item])

        result = self.run_renderer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "fixture_media image requires a raster image fixture", result.stderr
        )
        self.assertFalse(self.output_path.exists())

    def test_rejects_svg_image_fixture(self) -> None:
        module = load_renderer()
        module.ROOT = self.temp_dir
        fixture = (
            self.temp_dir
            / "evals"
            / "apple-platform-design"
            / "fixtures"
            / "synthetic-visual-injection.svg"
        )
        fixture.parent.mkdir(parents=True)
        fixture.write_text("<svg></svg>\n", encoding="utf-8")
        item = case("injection-01", "Non-portable image")
        item["fixture"] = (
            "evals/apple-platform-design/fixtures/synthetic-visual-injection.svg"
        )
        item["fixture_media"] = "image"
        item["capabilities"] = ["vision"]
        with self.assertRaisesRegex(
            ValueError, "fixture_media image requires a raster image fixture"
        ):
            module.validate_case(item, 1)

    def test_synthetic_visual_fixture_is_png_raster(self) -> None:
        payload = SYNTHETIC_VISUAL_FIXTURE.read_bytes()

        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(payload[12:16], b"IHDR")
        self.assertEqual(struct.unpack(">II", payload[16:24]), (800, 600))

    def test_rejects_png_extension_without_png_signature(self) -> None:
        module = load_renderer()
        module.ROOT = self.temp_dir
        fixture = (
            self.temp_dir
            / "evals"
            / "apple-platform-design"
            / "fixtures"
            / "not-a-raster.png"
        )
        fixture.parent.mkdir(parents=True)
        fixture.write_text(
            "synthetic text pretending to be an image", encoding="utf-8"
        )
        item = case("injection-02", "Fake raster")
        item["fixture"] = "evals/apple-platform-design/fixtures/not-a-raster.png"
        item["fixture_media"] = "image"
        item["capabilities"] = ["vision"]

        with self.assertRaisesRegex(ValueError, "PNG fixture is not PNG raster data"):
            module.validate_case(item, 1)

    def test_baseline_conditions_use_only_discovery_and_routing_cases(self) -> None:
        policy = json.loads(CONDITIONS.read_text(encoding="utf-8"))
        conditions = policy["conditions"]

        expected_baseline_kinds = ["discovery", "routing_completion"]
        self.assertEqual(
            conditions["no_skill"]["case_kinds"], expected_baseline_kinds
        )
        self.assertEqual(
            conditions["installed_hig_suite"]["case_kinds"],
            expected_baseline_kinds,
        )
        self.assertEqual(
            set(conditions["candidate"]["case_kinds"]),
            {
                "discovery",
                "routing_completion",
                "reasoning_invariant",
                "evidence",
                "injection",
                "ceiling",
            },
        )

    def test_calibration_scope_excludes_all_held_out_content(self) -> None:
        calibration = case("discovery-calibration", "Calibration title")
        held_out = case("discovery-held-out", "HELD OUT SECRET TITLE")
        held_out["split"] = "held_out"
        held_out["prompt"] = "HELD OUT SECRET PROMPT"
        held_out["expected"]["assertions"] = ["HELD OUT SECRET CRITERION"]
        self.write_cases([held_out, calibration])

        result = self.run_renderer(
            "--scope", "calibration", "--output", str(self.output_path)
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = self.output_path.read_text(encoding="utf-8")
        self.assertIn("discovery-calibration", rendered)
        self.assertNotIn("discovery-held-out", rendered)
        self.assertNotIn("HELD OUT SECRET TITLE", rendered)
        self.assertNotIn("HELD OUT SECRET PROMPT", rendered)
        self.assertNotIn("HELD OUT SECRET CRITERION", rendered)


if __name__ == "__main__":
    unittest.main()
