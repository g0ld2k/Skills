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

    def test_skill_names_reject_unicode_and_nfkc_lookalikes(self) -> None:
        for name in ("café", "ｔｅｓｔ"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                prefix="skill-validation-"
            ) as temp:
                skill_dir = Path(temp) / name
                skill_dir.mkdir()
                (skill_dir / "SKILL.md").write_text(
                    "---\n"
                    f"name: {name}\n"
                    "description: Use when testing portable skill names.\n"
                    "license: MIT\n"
                    "---\n",
                    encoding="utf-8",
                )
                errors: list[str] = []
                self.validator.validate_agent_skill_spec(skill_dir, errors)

            self.assertIn("must match the portable ASCII name grammar", "\n".join(errors))

    def test_malformed_frontmatter_is_reported_as_a_spec_error(self) -> None:
        errors = self.validate_spec("malformed-frontmatter")

        self.assertIn("Agent Skills spec", "\n".join(errors))
        self.assertIn("invalid YAML frontmatter", "\n".join(errors))

    def test_malformed_quoted_scalar_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_file = Path(temp) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: malformed-quoted-scalar\n"
                'description: "Use when testing \\q"\n'
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )

            frontmatter, parse_error = self.validator.parse_frontmatter(skill_file)

        self.assertEqual(frontmatter, {})
        self.assertIsNotNone(parse_error)
        self.assertIn("invalid YAML frontmatter", parse_error or "")

    def test_inline_comments_are_stripped_only_outside_quotes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_file = Path(temp) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: inline-comments\n"
                'description: "Use # literally when testing comments." # trailing\n'
                "license: MIT # SPDX identifier\n"
                "---\n",
                encoding="utf-8",
            )

            frontmatter, parse_error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNone(parse_error)
        self.assertEqual(frontmatter["license"], "MIT")
        self.assertEqual(
            frontmatter["description"], "Use # literally when testing comments."
        )

    def test_non_string_top_level_key_is_reported_through_spec_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp) / "top-level-key"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "7: unexpected\n"
                "name: top-level-key\n"
                "description: Use when testing top-level key types.\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            self.validator.validate_agent_skill_spec(skill_dir, errors)

        self.assertIn(
            "Field 'frontmatter' keys must be strings",
            "\n".join(errors),
        )

    def test_deep_inline_and_block_nesting_returns_a_spec_error(self) -> None:
        depth = 100
        inline_value = '{"a":' * depth + '"leaf"' + "}" * depth
        block_lines = ["metadata:"]
        for level in range(depth):
            block_lines.append("  " * (level + 1) + "a:")
        block_lines.append("  " * (depth + 1) + "leaf: value")

        for metadata in (f"metadata: {inline_value}", "\n".join(block_lines)):
            with self.subTest(metadata_style="inline" if metadata.startswith("metadata: {") else "block"):
                with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
                    skill_dir = Path(temp) / "deep-nesting"
                    skill_dir.mkdir()
                    (skill_dir / "SKILL.md").write_text(
                        "---\n"
                        "name: deep-nesting\n"
                        "description: Use when testing nesting limits.\n"
                        f"{metadata}\n"
                        "license: MIT\n"
                        "---\n",
                        encoding="utf-8",
                    )
                    errors: list[str] = []
                    try:
                        self.validator.validate_agent_skill_spec(skill_dir, errors)
                    except RecursionError as exc:
                        self.fail(f"deep nesting raised RecursionError: {exc}")

                self.assertIn("maximum YAML nesting depth", "\n".join(errors))

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

        def record(path: Path, errors: list[str]) -> dict[object, object] | None:
            calls.append(path)
            return original(path, errors)

        self.validator.validate_agent_skill_spec = record
        errors: list[str] = []
        configs = self.validator.load_package_configs(errors)
        canonical_names = [path.name for path in (ROOT / "skills").iterdir() if path.is_dir()]
        self.validator.validate_packaging(canonical_names, errors, configs)

        generated = {path for path in calls if "plugins" in path.parts}
        expected = {
            ROOT / "plugins" / config["name"] / "skills" / name
            for config in configs
            for name in config["skills"]
        }
        self.assertTrue(expected <= generated)
        self.assertIn("g0ld2k-apple-design", {config["name"] for config in configs})
        self.assertTrue(
            (ROOT / "plugins" / "g0ld2k-apple-design" / "skills").is_dir()
        )

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

    def test_validation_scenarios_require_content_for_each_label(self) -> None:
        for empty_label in ("Setup", "Prompt", "Pass"):
            with self.subTest(label=empty_label), tempfile.TemporaryDirectory(
                prefix="skill-validation-"
            ) as temp:
                skill_dir = Path(temp)
                references_dir = skill_dir / "references"
                references_dir.mkdir()
                sections = {
                    "Setup": "a repository is available",
                    "Prompt": "Use the skill on the repository.",
                    "Pass": "the skill reports the requested result.",
                }
                sections[empty_label] = ""
                scenario_text = "\n".join(
                    [
                        "# Validation Scenarios",
                        "",
                        "## Scenario 1: Happy path",
                        f"Setup: {sections['Setup']}",
                        f"Prompt: {sections['Prompt']}",
                        f"Pass: {sections['Pass']}",
                        "",
                        "## Scenario 2: Edge case",
                        "Setup: an edge case is available",
                        "Prompt: Use the skill for the edge case.",
                        "Pass: the edge case is handled.",
                        "",
                        "## Scenario 3: Adversarial",
                        "Setup: adversarial input is available",
                        "Prompt: Use the skill for adversarial input.",
                        "Pass: the input is handled safely.",
                    ]
                )
                (references_dir / "validation-scenarios.md").write_text(
                    scenario_text,
                    encoding="utf-8",
                )
                errors: list[str] = []
                self.validator.validate_validation_scenarios(skill_dir, errors)

            self.assertIn(
                f"Scenario 1: {empty_label} content must be non-empty",
                "\n".join(errors),
            )

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
