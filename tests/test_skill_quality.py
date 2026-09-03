#!/usr/bin/env python3
"""Behavioral quality gates for canonical skill instructions."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SKILL_BUDGETS = {
    "catch-me-up": {
        "ceiling": 1_550,
        "always_loaded": ("references/exploration-modes.md",),
    },
    "commit-message": {"ceiling": 600, "always_loaded": ()},
    "integration-branch-orchestrator": {
        "ceiling": 1_150,
        "always_loaded": (),
    },
    "pr-closeout-loop": {"ceiling": 1_900, "always_loaded": ()},
    "pr-comment-review": {
        "ceiling": 1_450,
        "always_loaded": (
            "references/conventions.md",
            "references/decision-rubric.md",
            "references/reply-templates.md",
        ),
    },
    "pr-generator": {
        "ceiling": 1_150,
        "always_loaded": ("references/conventions.md",),
    },
    "simplify": {"ceiling": 1_100, "always_loaded": ()},
    "testflight-notes": {
        "ceiling": 1_450,
        "always_loaded": (
            "references/classification-rules.md",
            "references/examples-good-bad.md",
            "references/format-guide.md",
        ),
    },
    "work-request-orchestration": {"ceiling": 1_200, "always_loaded": ()},
}


def count_instruction_words(skill_dir: Path, always_loaded: tuple[str, ...]) -> int:
    """Count tier-1 instructions plus references every valid run must load."""
    root = skill_dir.resolve()
    paths = [skill_dir / "SKILL.md"]
    for relative in always_loaded:
        path = (skill_dir / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise AssertionError(f"mandatory reference escapes skill directory: {relative}") from exc
        if not path.is_file():
            raise AssertionError(f"mandatory reference is not a file: {relative}")
        paths.append(path)
    return sum(len(path.read_text(encoding="utf-8").split()) for path in paths)


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate-skills-repo.py"
    spec = importlib.util.spec_from_file_location("validate_skills_repo", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    return module


class DescriptionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()

    def validate(self, name: str, description: object) -> list[str]:
        errors: list[str] = []
        self.validator.validate_skill_description(
            name,
            description,
            Path("skills") / name / "SKILL.md",
            errors,
        )
        return errors

    def test_explicit_only_skill_accepts_a_human_summary(self) -> None:
        self.assertEqual(
            self.validate(
                "integration-branch-orchestrator",
                "Supervise multi-PR integration work behind a promotion gate.",
            ),
            [],
        )

    def test_model_invoked_skill_requires_a_trigger_description(self) -> None:
        self.assertTrue(
            self.validate(
                "pr-generator",
                "Draft and publish pull request metadata.",
            )
        )

    def test_explicit_only_summary_is_one_line(self) -> None:
        self.assertTrue(
            self.validate(
                "work-request-orchestration",
                "Drive a work request.\nAcross multiple lines.",
            )
        )

    def test_explicit_only_summary_is_not_a_model_trigger(self) -> None:
        self.assertTrue(
            self.validate(
                "integration-branch-orchestrator",
                "Use when coordinating several pull requests.",
            )
        )

    def test_description_must_be_a_string(self) -> None:
        self.assertTrue(self.validate("pr-generator", True))


class FrontmatterParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()

    def test_unquoted_colon_space_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_file = Path(directory) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: sample-skill\n"
                "description: Use when drafting: publishing metadata.\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )

            _, error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNotNone(error)

    def parse_and_validate_description(self, name: str, scalar: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            skill_file = Path(directory) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                f"name: {name}\n"
                f"description: {scalar}\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )
            frontmatter, error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNone(error)
        errors: list[str] = []
        self.validator.validate_skill_description(
            name,
            frontmatter.get("description"),
            Path("skills") / name / "SKILL.md",
            errors,
        )
        return errors

    def test_double_quoted_newline_escape_is_validated_as_multiline(self) -> None:
        errors = self.parse_and_validate_description(
            "work-request-orchestration",
            r'"Human summary.\nSecond line."',
        )

        self.assertTrue(errors)

    def test_double_quoted_hex_escape_is_validated_after_decoding(self) -> None:
        errors = self.parse_and_validate_description(
            "integration-branch-orchestrator",
            r'"Use\x20when coordinating PRs."',
        )

        self.assertTrue(errors)

    def test_yaml_anchor_cannot_hide_an_explicit_only_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_file = Path(directory) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: integration-branch-orchestrator\n"
                "description: &summary Use when coordinating PRs.\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )

            _, error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNotNone(error)

    def test_unquoted_numeric_description_is_not_coerced_to_string(self) -> None:
        errors = self.parse_and_validate_description(
            "integration-branch-orchestrator",
            "42",
        )

        self.assertTrue(errors)

    def test_leading_zero_numeric_description_is_not_coerced_to_string(self) -> None:
        errors = self.parse_and_validate_description(
            "integration-branch-orchestrator",
            "01",
        )

        self.assertTrue(errors)

    def test_inline_comment_cannot_hide_a_numeric_description(self) -> None:
        errors = self.parse_and_validate_description(
            "integration-branch-orchestrator",
            "42 # human-looking summary",
        )

        self.assertTrue(errors)

    def test_folded_scalar_preserves_more_indented_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_file = Path(directory) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: integration-branch-orchestrator\n"
                "description: >-\n"
                "  Human\n"
                "    code\n"
                "  Summary\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )
            frontmatter, error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNone(error)
        self.assertEqual(frontmatter["description"], "Human\n  code\nSummary")
        errors: list[str] = []
        self.validator.validate_skill_description(
            "integration-branch-orchestrator",
            frontmatter["description"],
            Path("skills/integration-branch-orchestrator/SKILL.md"),
            errors,
        )
        self.assertTrue(errors)

    def test_clipped_block_summary_preserves_its_trailing_line_break(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_file = Path(directory) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: integration-branch-orchestrator\n"
                "description: |\n"
                "  Human summary.\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )
            frontmatter, error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNone(error)
        self.assertEqual(frontmatter["description"], "Human summary.\n")
        errors: list[str] = []
        self.validator.validate_skill_description(
            "integration-branch-orchestrator",
            frontmatter["description"],
            Path("skills/integration-branch-orchestrator/SKILL.md"),
            errors,
        )
        self.assertTrue(errors)

    def test_every_yaml_line_separator_breaks_a_one_line_summary(self) -> None:
        for escape in (r"\r", r"\v", r"\f", r"\N", r"\L", r"\P"):
            with self.subTest(escape=escape):
                errors = self.parse_and_validate_description(
                    "integration-branch-orchestrator",
                    f'"Human summary.{escape}Second line."',
                )
                self.assertTrue(errors)

    def test_trailing_yaml_line_separator_breaks_a_one_line_summary(self) -> None:
        errors = self.parse_and_validate_description(
            "integration-branch-orchestrator",
            r'"Human summary.\r"',
        )

        self.assertTrue(errors)

    def test_unsupported_double_quoted_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_file = Path(directory) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: sample-skill\n"
                r'description: "Use\qwhen drafting."' "\n"
                "---\n",
                encoding="utf-8",
            )

            _, error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNotNone(error)

    def test_quoted_boolean_remains_a_string(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_file = Path(directory) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: sample-skill\n"
                'description: "true"\n'
                "---\n",
                encoding="utf-8",
            )

            frontmatter, error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNone(error)
        self.assertEqual(frontmatter["description"], "true")


class SkillWordBudgetTests(unittest.TestCase):
    def test_declared_mandatory_references_count_toward_the_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_dir = Path(directory)
            (skill_dir / "references").mkdir()
            (skill_dir / "SKILL.md").write_text("one two", encoding="utf-8")
            (skill_dir / "references" / "required.md").write_text(
                "three four five", encoding="utf-8"
            )

            total = count_instruction_words(
                skill_dir,
                ("references/required.md",),
            )

        self.assertEqual(total, 5)

    def test_each_skill_stays_within_its_budget(self) -> None:
        actual_names = {
            path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(actual_names, set(SKILL_BUDGETS))

        for name, budget in SKILL_BUDGETS.items():
            with self.subTest(skill=name):
                total = count_instruction_words(
                    ROOT / "skills" / name,
                    budget["always_loaded"],
                )
                self.assertLessEqual(total, budget["ceiling"])


if __name__ == "__main__":
    unittest.main()
