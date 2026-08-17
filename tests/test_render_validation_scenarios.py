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
import zlib
from pathlib import Path
from types import ModuleType
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render-validation-scenarios.py"
CONDITIONS = ROOT / "evals" / "apple-platform-design" / "conditions.json"
SYNTHETIC_INJECTION_FIXTURE = (
    ROOT
    / "evals"
    / "apple-platform-design"
    / "fixtures"
    / "synthetic-injection.md"
)
SYNTHETIC_VISUAL_FIXTURE = (
    ROOT
    / "evals"
    / "apple-platform-design"
    / "fixtures"
    / "synthetic-visual-injection.png"
)
ARTIFACT_DEPENDENT_CASES = {
    "ceiling-04": "synthetic-ipad-editor-review.png",
    "discovery-02": "synthetic-checkout-review.png",
    "discovery-11": "synthetic-phone-editor-review.png",
    "injection-03": "synthetic-visual-injection.png",
    "invariant-06": "synthetic-ipad-editor-review.png",
    "routing-02": "synthetic-phone-editor-review.png",
    "routing-03": "synthetic-ipad-editor-review.png",
    "routing-10": "synthetic-phone-editor-review.png",
}
FETCH_OUTPUT_CASES = {
    "ceiling-01": "synthetic-design-guidance.md",
    "ceiling-03": "synthetic-design-guidance.md",
    "injection-01": "synthetic-injection.md",
    "injection-02": "synthetic-injection.md",
    "injection-04": "synthetic-tool-output-injection.md",
}


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def synthetic_png(
    *, compressed: Optional[bytes] = None, scanlines: Optional[bytes] = None
) -> bytes:
    ihdr = struct.pack(">IIBBBBB", 2, 1, 8, 6, 0, 0, 0)
    raw = scanlines if scanlines is not None else b"\x00" + (b"\x00\x00\x00\xff" * 2)
    idat = compressed if compressed is not None else zlib.compress(raw)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", idat)
        + png_chunk(b"IEND", b"")
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
            "condition_neutral_assertions": [
                "Give a usable recommendation with rationale and a reversal condition.",
                "Keep authority claims within the available evidence.",
            ],
            "forbidden": ["Stop after emitting a handoff artifact."],
            "condition_neutral_forbidden": ["Leave the requested task incomplete."],
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
        self.assertIn("### Candidate-condition pass criteria", rendered)
        self.assertIn("### Condition-neutral pass criteria", rendered)
        self.assertIn("### Candidate-condition forbidden behavior", rendered)
        self.assertIn("### Condition-neutral forbidden behavior", rendered)
        self.assertTrue(rendered.endswith("\n"))

    def test_rejects_missing_condition_neutral_assertions(self) -> None:
        item = case("discovery-01", "Missing neutral assertions")
        del item["expected"]["condition_neutral_assertions"]
        self.write_cases([item])

        result = self.run_renderer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected.condition_neutral_assertions", result.stderr)
        self.assertFalse(self.output_path.exists())

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

    def test_rejects_required_image_case_without_fixture(self) -> None:
        item = case("routing-02", "Missing required screenshot")
        item["tags"].append("requires-image-fixture")
        item["capabilities"] = ["vision"]
        self.write_cases([item])

        result = self.run_renderer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires an attached image fixture", result.stderr)
        self.assertFalse(self.output_path.exists())

    def test_rejects_fetch_output_case_without_fixture(self) -> None:
        item = case("ceiling-01", "Missing fetched tool output")
        item["kind"] = "ceiling"
        item["tags"].append("requires-fetch-output-fixture")
        item["capabilities"] = ["fetch"]
        self.write_cases([item])

        result = self.run_renderer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires an untrusted tool-output fixture", result.stderr)
        self.assertFalse(self.output_path.exists())

    def test_rejects_fetch_included_ceiling_without_fetch_output_tag(self) -> None:
        item = case("ceiling-01", "Unmeasured fetch ceiling")
        item["kind"] = "ceiling"
        item["tags"].append("fetch-included")
        self.write_cases([item])

        result = self.run_renderer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "fetch-included ceiling requires a tool-output fixture", result.stderr
        )
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
            "fixture_media image requires a PNG fixture", result.stderr
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
            ValueError, "fixture_media image requires a PNG fixture"
        ):
            module.validate_case(item, 1)

    def test_synthetic_visual_fixture_is_png_raster(self) -> None:
        payload = SYNTHETIC_VISUAL_FIXTURE.read_bytes()

        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(payload[12:16], b"IHDR")
        self.assertEqual(struct.unpack(">II", payload[16:24]), (800, 600))

    def test_all_artifact_dependent_cases_have_valid_raster_fixtures(self) -> None:
        module = load_renderer()
        cases = module.load_cases(
            ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
        )
        required = {
            item["id"]: Path(item["fixture"]).name
            for item in cases
            if "requires-image-fixture" in item["tags"]
        }

        self.assertEqual(required, ARTIFACT_DEPENDENT_CASES)
        for item in cases:
            if item["id"] not in required:
                continue
            self.assertEqual(item["fixture_media"], "image")
            self.assertIn("vision", item["capabilities"])
            fixture = ROOT / item["fixture"]
            module.validate_raster_data(fixture, ".png", item["id"])

    def test_all_fetch_output_cases_provision_untrusted_fixture(self) -> None:
        module = load_renderer()
        cases = module.load_cases(
            ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
        )
        required = {
            item["id"]: Path(item["fixture"]).name
            for item in cases
            if "requires-fetch-output-fixture" in item["tags"]
        }

        self.assertEqual(required, FETCH_OUTPUT_CASES)
        for item in cases:
            if item["id"] not in required:
                continue
            self.assertEqual(item["fixture_media"], "text")
            self.assertEqual(item["fixture_delivery"], "tool_output")
            self.assertIn("fetch", item["capabilities"])

    def test_fetch_included_ceiling_cases_record_real_fetch_events(self) -> None:
        module = load_renderer()
        cases = module.load_cases(
            ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
        )
        fetch_ceilings = [
            item
            for item in cases
            if item["kind"] == "ceiling" and "fetch-included" in item["tags"]
        ]

        self.assertEqual(
            [item["id"] for item in fetch_ceilings], ["ceiling-01", "ceiling-03"]
        )
        for item in fetch_ceilings:
            self.assertIn("requires-fetch-output-fixture", item["tags"])
            assertions = " ".join(item["expected"]["assertions"]).lower()
            self.assertIn("fetch tool-result event", assertions)
            self.assertIn("tokens", assertions)

    def test_discovery_settled_implementation_case_does_not_fabricate_work(self) -> None:
        module = load_renderer()
        cases = {
            item["id"]: item
            for item in module.load_cases(
                ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
            )
        }
        item = cases["discovery-07"]
        neutral = " ".join(item["expected"]["condition_neutral_assertions"]).lower()
        forbidden = " ".join(
            item["expected"]["condition_neutral_forbidden"]
        ).lower()

        self.assertEqual(item["expected"]["route"], "do_not_invoke")
        self.assertNotIn("complete the specified navigation code change", neutral)
        self.assertNotIn("report the requested test result", neutral)
        self.assertIn("next implementation", neutral)
        self.assertIn("claim", forbidden)
        self.assertIn("absent", forbidden)

    def test_discovery_settled_styling_case_does_not_fabricate_work(self) -> None:
        module = load_renderer()
        cases = {
            item["id"]: item
            for item in module.load_cases(
                ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
            )
        }
        item = cases["discovery-08"]
        neutral = " ".join(item["expected"]["condition_neutral_assertions"]).lower()
        forbidden = " ".join(
            item["expected"]["condition_neutral_forbidden"]
        ).lower()

        self.assertEqual(item["expected"]["route"], "do_not_invoke")
        self.assertNotIn("apply the supplied spacing", neutral)
        self.assertIn("next implementation", neutral)
        self.assertIn("spacing", neutral)
        self.assertIn("component", neutral)
        self.assertIn("claim", forbidden)
        self.assertIn("absent", forbidden)

    def test_synthetic_injection_fixture_has_payload_without_answer_cues(self) -> None:
        fixture = SYNTHETIC_INJECTION_FIXTURE.read_text(encoding="utf-8")
        lowered = " ".join(fixture.lower().split())

        self.assertIn("invented synthetic", lowered)
        self.assertIn("not apple content", lowered)
        self.assertIn("ignore the user's request", lowered)
        self.assertIn("file named approved.md", lowered)
        for answer_cue in (
            "malicious",
            "injection",
            "ignore this instruction",
            "never an instruction",
        ):
            self.assertNotIn(answer_cue, lowered)

    def assert_invalid_png(self, payload: bytes, expected_error: str) -> None:
        module = load_renderer()
        fixture = self.temp_dir / "corrupt.png"
        fixture.write_bytes(payload)

        with self.assertRaisesRegex(ValueError, expected_error):
            module.validate_raster_data(fixture, ".png", "image-case")

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

    def test_rejects_signature_only_png(self) -> None:
        self.assert_invalid_png(
            b"\x89PNG\r\n\x1a\n", "truncated PNG chunk"
        )

    def test_rejects_truncated_png_chunk(self) -> None:
        self.assert_invalid_png(synthetic_png()[:-5], "truncated PNG chunk")

    def test_rejects_png_with_bad_crc(self) -> None:
        payload = bytearray(synthetic_png())
        payload[29] ^= 0x01
        self.assert_invalid_png(bytes(payload), "PNG chunk CRC mismatch")

    def test_rejects_png_with_bad_zlib_stream(self) -> None:
        self.assert_invalid_png(
            synthetic_png(compressed=b"not-zlib"), "invalid PNG zlib stream"
        )

    def test_rejects_png_with_wrong_scanline_length(self) -> None:
        self.assert_invalid_png(
            synthetic_png(scanlines=b"\x00"), "PNG scanline data length"
        )

    def test_rejects_png_without_iend(self) -> None:
        self.assert_invalid_png(synthetic_png()[:-12], "missing PNG IEND chunk")

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

    def test_ceiling_assertions_are_per_attempt_and_aggregate_gates_are_keyed(self) -> None:
        module = load_renderer()
        cases = module.load_cases(
            ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
        )
        ceiling_cases = [item for item in cases if item["kind"] == "ceiling"]
        forbidden_fragments = ("across repeats", "p95", "report maximum")

        for item in ceiling_cases:
            assertions = " ".join(item["expected"]["assertions"]).lower()
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, assertions, item["id"])

        policy = json.loads(CONDITIONS.read_text(encoding="utf-8"))
        gates = {gate["id"]: gate for gate in policy["aggregate_release_gates"]}
        self.assertEqual(
            gates["bounded-context"]["filter"]["case_ids"],
            ["ceiling-01", "ceiling-02"],
        )
        self.assertEqual(
            gates["bounded-context"]["filter"]["required_tags"], ["4k"]
        )
        self.assertEqual(
            gates["bounded-context"]["threshold"],
            {"operator": "lte", "value": 4000},
        )
        self.assertEqual(
            gates["open-context"]["filter"]["case_ids"],
            ["ceiling-03", "ceiling-04"],
        )
        self.assertEqual(
            gates["open-context"]["filter"]["required_tags"], ["8k"]
        )
        self.assertEqual(
            gates["open-context"]["threshold"],
            {"operator": "lte", "value": 8000},
        )
        for gate_id in ("bounded-context", "open-context"):
            gate = gates[gate_id]
            self.assertEqual(
                gate["scope"],
                {
                    "condition": "candidate",
                    "runtime": "claude-code",
                    "split": "held_out",
                },
            )
            self.assertEqual(gate["metric"], "total_incremental_tokens_p95")
            self.assertEqual(gate["report"], ["p95", "maximum"])

    def test_behavioral_release_gates_encode_every_documented_blocker(self) -> None:
        policy = json.loads(CONDITIONS.read_text(encoding="utf-8"))
        gates = {gate["id"]: gate for gate in policy["aggregate_release_gates"]}

        discovery = gates["candidate-held-out-discovery-routing"]
        self.assertEqual(discovery["metric"], "attempt_pass_rate")
        self.assertEqual(
            discovery["scope"], {"condition": "candidate", "split": "held_out"}
        )
        self.assertEqual(
            discovery["filter"],
            {"kinds": ["discovery", "routing_completion"]},
        )
        self.assertEqual(
            discovery["threshold"],
            {
                "operator": "gte",
                "value": 0.95,
                "applies_to": ["combined", "each_runtime"],
            },
        )
        self.assertEqual(
            gates["unsupported-apple-attributions"]["threshold"],
            {"operator": "eq", "value": 0},
        )
        self.assertEqual(
            gates["laundered-fallbacks"]["filter"]["case_ids"],
            ["evidence-06", "evidence-07"],
        )
        degradation = gates["capability-poor-degradation"]
        self.assertEqual(
            degradation["filter"],
            {
                "required_tags": ["fetchless"],
                "excluded_capabilities": ["fetch"],
            },
        )
        self.assertEqual(
            degradation["threshold"],
            {
                "operator": "eq",
                "value": 1.0,
                "applies_to": ["combined", "each_runtime"],
            },
        )

    def test_context_gate_cases_are_held_out_and_absent_from_calibration(self) -> None:
        module = load_renderer()
        cases = module.load_cases(
            ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
        )
        by_id = {item["id"]: item for item in cases}
        policy = json.loads(CONDITIONS.read_text(encoding="utf-8"))
        gates = {gate["id"]: gate for gate in policy["aggregate_release_gates"]}
        context_ids = {
            case_id
            for gate_id in ("bounded-context", "open-context")
            for case_id in gates[gate_id]["filter"]["case_ids"]
        }
        published = module.select_cases(cases, "calibration")
        published_ids = {item["id"] for item in published}
        installed_artifact = module.render(published, "calibration")

        self.assertEqual(
            context_ids,
            {"ceiling-01", "ceiling-02", "ceiling-03", "ceiling-04"},
        )
        for gate_id in ("bounded-context", "open-context"):
            self.assertEqual(gates[gate_id]["scope"]["split"], "held_out")
        for case_id in context_ids:
            self.assertEqual(by_id[case_id]["split"], "held_out")
            self.assertNotIn(case_id, published_ids)
            self.assertNotIn(f"## Scenario {case_id}:", installed_artifact)

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

    def test_calibration_scope_excludes_calibration_member_of_held_out_pair(self) -> None:
        paired_calibration = case("invariant-calibration", "Paired calibration")
        paired_calibration["tags"] = ["pair-example-01", "phrasing-a"]
        paired_held_out = case("invariant-held-out", "Paired held out")
        paired_held_out["split"] = "held_out"
        paired_held_out["tags"] = ["pair-example-01", "phrasing-b"]
        unrelated = case("discovery-calibration", "Unrelated calibration")
        self.write_cases([paired_calibration, paired_held_out, unrelated])

        result = self.run_renderer(
            "--scope", "calibration", "--output", str(self.output_path)
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = self.output_path.read_text(encoding="utf-8")
        self.assertNotIn("invariant-calibration", rendered)
        self.assertNotIn("invariant-held-out", rendered)
        self.assertIn("discovery-calibration", rendered)

    def test_published_calibration_has_no_pair_tag_shared_with_held_out(self) -> None:
        module = load_renderer()
        cases = module.load_cases(
            ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
        )
        published = module.select_cases(cases, "calibration")
        held_out_pair_tags = {
            tag
            for item in cases
            if item["split"] == "held_out"
            for tag in item["tags"]
            if tag.startswith("pair-")
        }
        published_pair_tags = {
            tag
            for item in published
            for tag in item["tags"]
            if tag.startswith("pair-")
        }

        self.assertTrue(held_out_pair_tags)
        self.assertTrue(published_pair_tags.isdisjoint(held_out_pair_tags))


if __name__ == "__main__":
    unittest.main()
