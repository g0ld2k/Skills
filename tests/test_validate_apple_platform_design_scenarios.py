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
    template = str(
        Path(os.environ.get("TMPDIR") or "/tmp")
        / "apple-design-validator-tests.XXXXXX"
    )
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
            "condition_neutral_assertions": [
                "Give a useful container recommendation with rationale."
            ],
            "forbidden": [],
            "condition_neutral_forbidden": [],
        },
    }


def minimal_context_case(case_id: str) -> dict[str, object]:
    item = minimal_case()
    item.update(
        {
            "id": case_id,
            "kind": "ceiling",
            "split": "held_out",
            "title": f"Context case {case_id}",
            "tags": ["claude-code", "context-gate"],
            "setup": "A synthetic context measurement case is supplied.",
            "prompt": "Record this attempt's total incremental token count.",
        }
    )
    item["expected"]["route"] = "already_invoked"
    return item


def valid_conditions() -> dict[str, object]:
    all_kinds = [
        "discovery",
        "routing_completion",
        "reasoning_invariant",
        "evidence",
        "injection",
        "ceiling",
    ]
    candidate_assertions = [
        "expected.assertions",
        "expected.condition_neutral_assertions",
    ]
    candidate_forbidden = [
        "expected.forbidden",
        "expected.condition_neutral_forbidden",
    ]
    neutral_assertions = ["expected.condition_neutral_assertions"]
    neutral_forbidden = ["expected.condition_neutral_forbidden"]
    return {
        "schema_version": 2,
        "candidate_answer_keys": ["expected.route", "expected.references"],
        "aggregate_release_gates": [
            {
                "id": "candidate-held-out-discovery-routing",
                "metric": "attempt_pass_rate",
                "scope": {"condition": "candidate", "split": "held_out"},
                "filter": {"kinds": ["discovery", "routing_completion"]},
                "threshold": {
                    "operator": "gte",
                    "value": 0.95,
                    "applies_to": ["combined", "each_runtime"],
                },
                "report": ["combined", "by_runtime", "numerator", "denominator"],
            },
            {
                "id": "unsupported-apple-attributions",
                "metric": "unsupported_apple_attribution_count",
                "scope": {"attempts": "all"},
                "filter": {},
                "threshold": {"operator": "eq", "value": 0},
                "report": ["count", "case_ids", "by_runtime", "by_condition"],
            },
            {
                "id": "laundered-fallbacks",
                "metric": "laundered_fallback_count",
                "scope": {"condition": "candidate", "attempts": "all"},
                "filter": {"case_ids": ["evidence-06", "evidence-07"]},
                "threshold": {"operator": "eq", "value": 0},
                "report": ["count", "case_ids", "by_runtime"],
            },
            {
                "id": "capability-poor-degradation",
                "metric": "correct_degradation_pass_rate",
                "scope": {"condition": "candidate", "attempts": "all"},
                "filter": {
                    "required_tags": ["fetchless"],
                    "excluded_capabilities": ["fetch"],
                },
                "threshold": {
                    "operator": "eq",
                    "value": 1.0,
                    "applies_to": ["combined", "each_runtime"],
                },
                "report": [
                    "combined",
                    "by_runtime",
                    "numerator",
                    "denominator",
                    "case_ids",
                ],
            },
            {
                "id": "bounded-context",
                "metric": "total_incremental_tokens_p95",
                "scope": {
                    "condition": "candidate",
                    "runtime": "claude-code",
                    "split": "held_out",
                },
                "filter": {
                    "case_ids": ["ceiling-01", "ceiling-02"],
                    "required_tags": ["4k"],
                },
                "threshold": {"operator": "lte", "value": 4000},
                "report": ["p95", "maximum"],
            },
            {
                "id": "open-context",
                "metric": "total_incremental_tokens_p95",
                "scope": {
                    "condition": "candidate",
                    "runtime": "claude-code",
                    "split": "held_out",
                },
                "filter": {
                    "case_ids": ["ceiling-03", "ceiling-04"],
                    "required_tags": ["8k"],
                },
                "threshold": {"operator": "lte", "value": 8000},
                "report": ["p95", "maximum"],
            },
        ],
        "conditions": {
            "candidate": {
                "namespace": "candidate skill with competing namespace",
                "case_kinds": all_kinds,
                "route_scoring": "gate",
                "reference_scoring": "gate",
                "assertion_keys": candidate_assertions,
                "forbidden_keys": candidate_forbidden,
                "condition_neutral_quality_scoring": "gate",
            },
            "no_skill": {
                "namespace": "candidate and overlapping suite absent",
                "case_kinds": ["discovery", "routing_completion"],
                "candidate_setup_clauses": "omit",
                "route_scoring": "descriptive",
                "reference_scoring": "descriptive",
                "assertion_keys": neutral_assertions,
                "forbidden_keys": neutral_forbidden,
                "condition_neutral_quality_scoring": "gate",
            },
            "installed_hig_suite": {
                "namespace": "candidate absent and HIG suite present",
                "case_kinds": ["discovery", "routing_completion"],
                "candidate_setup_clauses": "omit",
                "route_scoring": "descriptive",
                "reference_scoring": "descriptive",
                "assertion_keys": neutral_assertions,
                "forbidden_keys": neutral_forbidden,
                "condition_neutral_quality_scoring": "gate",
            },
        },
        "condition_neutral_dimensions": ["task_quality", "evidence", "completion"],
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
        self.module.APPLE_DESIGN_CONDITIONS = (
            self.temp_dir / "evals" / "apple-platform-design" / "conditions.json"
        )
        self.module.APPLE_DESIGN_CONDITIONS.parent.mkdir(parents=True, exist_ok=True)
        self.module.APPLE_DESIGN_CONDITIONS.write_text(
            json.dumps(valid_conditions()) + "\n", encoding="utf-8"
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
        self.module.APPLE_DESIGN_CONDITIONS.write_text(
            json.dumps(valid_conditions()) + "\n", encoding="utf-8"
        )
        cases = [
            minimal_case(),
            *[
                minimal_context_case(case_id)
                for case_id in (
                    "ceiling-01",
                    "ceiling-02",
                    "ceiling-03",
                    "ceiling-04",
                )
            ],
        ]
        self.module.APPLE_DESIGN_CASES.write_text(
            "".join(json.dumps(item) + "\n" for item in cases),
            encoding="utf-8",
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

    def validate_with_conditions(self, policy: object) -> list[str]:
        self.write_valid_wave1_artifacts()
        if isinstance(policy, str):
            self.module.APPLE_DESIGN_CONDITIONS.write_text(policy, encoding="utf-8")
        else:
            self.module.APPLE_DESIGN_CONDITIONS.write_text(
                json.dumps(policy) + "\n", encoding="utf-8"
            )
        errors: list[str] = []
        self.module.validate_apple_platform_design_scenarios(errors)
        return errors

    def test_missing_skill_target_no_ops_after_wave1_validation(self) -> None:
        self.write_valid_wave1_artifacts()
        errors: list[str] = []

        self.module.validate_apple_platform_design_scenarios(errors)

        self.assertEqual(errors, [])

    def test_reports_missing_conditions_policy(self) -> None:
        self.write_valid_wave1_artifacts()
        self.module.APPLE_DESIGN_CONDITIONS.unlink()
        errors: list[str] = []

        self.module.validate_apple_platform_design_scenarios(errors)

        self.assertEqual(
            errors, ["evals/apple-platform-design/conditions.json: missing"]
        )

    def test_reports_invalid_conditions_json(self) -> None:
        errors = self.validate_with_conditions("{not-json}\n")

        self.assertEqual(len(errors), 1)
        self.assertIn("conditions.json: invalid JSON", errors[0])

    def test_reports_missing_and_extra_conditions(self) -> None:
        missing = valid_conditions()
        del missing["conditions"]["no_skill"]
        missing_errors = self.validate_with_conditions(missing)

        extra = valid_conditions()
        extra["conditions"]["experimental"] = extra["conditions"]["candidate"]
        extra_errors = self.validate_with_conditions(extra)

        self.assertTrue(
            any("missing conditions: no_skill" in error for error in missing_errors)
        )
        self.assertTrue(
            any("extra conditions: experimental" in error for error in extra_errors)
        )

    def test_reports_misspelled_scoring_enum(self) -> None:
        policy = valid_conditions()
        policy["conditions"]["candidate"]["route_scoring"] = "gated"

        errors = self.validate_with_conditions(policy)

        self.assertTrue(
            any("candidate.route_scoring must be gate" in error for error in errors)
        )

    def test_reports_incorrect_condition_case_kind_scope(self) -> None:
        policy = valid_conditions()
        policy["conditions"]["no_skill"]["case_kinds"] = ["discovery"]

        errors = self.validate_with_conditions(policy)

        self.assertTrue(any("no_skill.case_kinds" in error for error in errors))

    def test_reports_malformed_candidate_answer_keys(self) -> None:
        policies = []
        wrong_type = valid_conditions()
        wrong_type["candidate_answer_keys"] = "expected.route"
        policies.append(wrong_type)
        wrong_value = valid_conditions()
        wrong_value["candidate_answer_keys"] = [
            "expected.route",
            "expected.assertions",
        ]
        policies.append(wrong_value)

        for policy in policies:
            with self.subTest(policy=policy["candidate_answer_keys"]):
                errors = self.validate_with_conditions(policy)
                self.assertTrue(
                    any("candidate_answer_keys" in error for error in errors)
                )

    def test_reports_omitted_behavioral_release_gate(self) -> None:
        policy = valid_conditions()
        policy["aggregate_release_gates"] = [
            gate
            for gate in policy["aggregate_release_gates"]
            if gate["id"] != "unsupported-apple-attributions"
        ]

        errors = self.validate_with_conditions(policy)

        self.assertTrue(
            any(
                "aggregate_release_gates must match every release blocker" in error
                for error in errors
            )
        )

    def test_reports_malformed_behavioral_release_gate_threshold(self) -> None:
        policy = valid_conditions()
        policy["aggregate_release_gates"][0]["threshold"] = {
            "operator": "gte",
            "value": 95,
        }

        errors = self.validate_with_conditions(policy)

        self.assertTrue(
            any(
                "aggregate_release_gates must match every release blocker" in error
                for error in errors
            )
        )

    def test_reports_malformed_behavioral_release_gate_scope(self) -> None:
        policy = valid_conditions()
        policy["aggregate_release_gates"][2]["scope"] = {
            "condition": "candidate",
            "split": "held_out",
        }

        errors = self.validate_with_conditions(policy)

        self.assertTrue(
            any(
                "aggregate_release_gates must match every release blocker" in error
                for error in errors
            )
        )

    def test_reports_malformed_context_release_gate(self) -> None:
        policy = valid_conditions()
        policy["aggregate_release_gates"][5]["threshold"]["value"] = 4000

        errors = self.validate_with_conditions(policy)

        self.assertTrue(
            any(
                "aggregate_release_gates must match every release blocker" in error
                for error in errors
            )
        )

    def test_reports_context_gate_without_held_out_scope(self) -> None:
        policy = valid_conditions()
        del policy["aggregate_release_gates"][4]["scope"]["split"]

        errors = self.validate_with_conditions(policy)

        self.assertTrue(
            any(
                "aggregate_release_gates must match every release blocker" in error
                for error in errors
            )
        )

    def test_reports_context_gate_referencing_calibration_case(self) -> None:
        self.write_valid_wave1_artifacts()
        cases = [
            json.loads(line)
            for line in self.module.APPLE_DESIGN_CASES.read_text(
                encoding="utf-8"
            ).splitlines()
        ]
        for item in cases:
            if item["id"] == "ceiling-01":
                item["split"] = "calibration"
        self.module.APPLE_DESIGN_CASES.write_text(
            "".join(json.dumps(item) + "\n" for item in cases),
            encoding="utf-8",
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
        errors: list[str] = []

        self.module.validate_apple_platform_design_scenarios(errors)

        self.assertTrue(
            any(
                "bounded-context case ceiling-01 must be held_out" in error
                for error in errors
            )
        )

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
