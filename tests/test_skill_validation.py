#!/usr/bin/env python3
"""Focused Agent Skills conformance and house-policy tests."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "invalid-skills"


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate-skills-repo.py"
    spec = importlib.util.spec_from_file_location("validate_skills_repo", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentSkillsConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()

    def validate_spec(self, fixture_name: str) -> list[str]:
        errors: list[str] = []
        self.validator.validate_agent_skill_spec(FIXTURES / fixture_name, errors)
        return errors

    def test_invalid_field_types_are_reported_as_spec_errors(self) -> None:
        errors = self.validate_spec("invalid-field-types")

        self.assertTrue(any("Agent Skills spec" in error for error in errors))
        self.assertIn("Field 'name' must be a non-empty string", "\n".join(errors))
        self.assertIn("Field 'description' must be a non-empty string", "\n".join(errors))
        self.assertIn("Field 'license' must be a string", "\n".join(errors))
        self.assertIn("Field 'compatibility' must be a string", "\n".join(errors))
        self.assertIn("Field 'metadata' must be a mapping", "\n".join(errors))
        self.assertIn("Field 'allowed-tools' must be a string", "\n".join(errors))

    def test_overlong_values_are_reported_with_spec_limits(self) -> None:
        errors = self.validate_spec("overlong-values")

        joined = "\n".join(errors)
        self.assertIn("Description exceeds 1024 character limit", joined)
        self.assertIn("Compatibility exceeds 500 character limit", joined)

    def test_name_directory_mismatch_is_reported_as_spec_error(self) -> None:
        errors = self.validate_spec("mismatched-directory")

        self.assertIn("Directory name 'mismatched-directory' must match skill name 'declared-name'", errors[0])

    def test_unsupported_frontmatter_is_reported_as_spec_error(self) -> None:
        errors = self.validate_spec("unsupported-frontmatter")

        self.assertIn("unsupported frontmatter field 'tools'", "\n".join(errors))

    def test_metadata_keys_values_and_nested_values_must_be_strings(self) -> None:
        errors = self.validate_spec("metadata-entry-types")

        joined = "\n".join(errors)
        self.assertIn("Field 'metadata' keys must be strings", joined)
        self.assertIn("Field 'metadata' values must be strings", joined)

    def test_name_syntax_and_exact_skill_filename_are_spec_requirements(self) -> None:
        errors = self.validate_spec("invalid-name")
        joined = "\n".join(errors)

        self.assertIn("must be lowercase", joined)
        self.assertIn("cannot start or end with a hyphen", joined)
        self.assertIn("cannot contain consecutive hyphens", joined)
        self.assertIn("contains invalid characters", joined)

        errors = self.validate_spec("wrong-skill-file-case")
        self.assertIn("missing required file: SKILL.md", "\n".join(errors))

    def test_malformed_frontmatter_is_reported_as_a_spec_error(self) -> None:
        errors = self.validate_spec("malformed-frontmatter")

        self.assertIn("Agent Skills spec", "\n".join(errors))
        self.assertIn("invalid YAML frontmatter", "\n".join(errors))

    def test_whitespace_values_are_rejected_and_exact_limits_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            temp_path = Path(temp)
            whitespace = temp_path / "whitespace"
            whitespace.mkdir()
            (whitespace / "SKILL.md").write_text(
                "---\n"
                "name: whitespace\n"
                "description: '   '\n"
                "license: MIT\n"
                "compatibility: '   '\n"
                "---\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            self.validator.validate_agent_skill_spec(whitespace, errors)
            self.assertIn("Field 'description' must be a non-empty string", "\n".join(errors))
            self.assertIn("Field 'compatibility' must be a non-empty string", "\n".join(errors))

            boundary = temp_path / "boundary"
            boundary.mkdir()
            (boundary / "SKILL.md").write_text(
                "---\n"
                "name: boundary\n"
                f"description: {'a' * 1024}\n"
                f"compatibility: {'b' * 500}\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )
            errors = []
            self.validator.validate_agent_skill_spec(boundary, errors)
            self.assertEqual(errors, [])

    def test_generated_skill_copies_are_independently_traversed(self) -> None:
        calls: list[Path] = []
        original = self.validator.validate_agent_skill_spec

        def record(path: Path, errors: list[str]) -> dict[str, object] | None:
            calls.append(path)
            return original(path, errors)

        self.validator.validate_agent_skill_spec = record
        errors: list[str] = []
        configs = self.validator.load_package_configs(errors)
        canonical_names = [path.name for path in (ROOT / "skills").iterdir() if path.is_dir()]
        self.validator.validate_packaging(canonical_names, errors, configs)

        generated = {path for path in calls if "plugins" in path.parts}
        expected = {
            ROOT / "plugins" / "g0ld2k-skills" / "skills" / name
            for config in configs
            for name in config["skills"]
        }
        self.assertTrue(expected <= generated)

    def test_conformance_source_is_pinned_and_network_independent(self) -> None:
        self.assertEqual(
            self.validator.AGENT_SKILLS_SPEC_URL,
            "https://agentskills.io/specification",
        )
        self.assertRegex(
            self.validator.AGENT_SKILLS_SPEC_REVISION,
            r"^[0-9a-f]{40}$",
        )

    def test_scenario_convention_covers_non_exempt_canonical_skills(self) -> None:
        self.assertEqual(
            self.validator.VALIDATION_SCENARIO_EXEMPTIONS,
            {"commit-message", "pr-generator", "testflight-notes"},
        )
        for skill_dir in sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir()):
            if skill_dir.name in self.validator.VALIDATION_SCENARIO_EXEMPTIONS:
                continue
            with self.subTest(skill=skill_dir.name):
                errors: list[str] = []
                self.validator.validate_validation_scenarios(skill_dir, errors)
                self.assertEqual(errors, [])

    def test_house_policy_diagnostics_are_separate_from_spec_errors(self) -> None:
        frontmatter, parse_error = self.validator.parse_frontmatter(
            FIXTURES / "house-policy-violations" / "SKILL.md"
        )
        self.assertIsNone(parse_error)
        spec_errors: list[str] = []
        self.validator.validate_agent_skill_spec(
            FIXTURES / "house-policy-violations", spec_errors
        )
        self.assertEqual(spec_errors, [])

        policy_errors: list[str] = []
        self.validator.validate_house_policies(
            FIXTURES / "house-policy-violations", frontmatter, policy_errors
        )
        self.assertTrue(policy_errors)
        self.assertTrue(all("House policy" in error for error in policy_errors))
        self.assertIn("description must start with 'Use when'", "\n".join(policy_errors))
        self.assertIn("license must be MIT", "\n".join(policy_errors))
        self.assertIn("allowed-tools is not permitted", "\n".join(policy_errors))


if __name__ == "__main__":
    unittest.main()
