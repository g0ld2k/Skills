#!/usr/bin/env python3
"""Behavioral quality gates for canonical skill instructions."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
WORD_BUDGETS = {
    "catch-me-up": 800,
    "commit-message": 600,
    "integration-branch-orchestrator": 1_150,
    "pr-closeout-loop": 1_900,
    "pr-comment-review": 900,
    "pr-generator": 950,
    "simplify": 1_100,
    "testflight-notes": 600,
    "work-request-orchestration": 1_200,
}


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

    def validate(self, name: str, description: str) -> list[str]:
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


class SkillWordBudgetTests(unittest.TestCase):
    def test_each_skill_stays_within_its_budget(self) -> None:
        actual_names = {
            path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(actual_names, set(WORD_BUDGETS))

        for name, budget in WORD_BUDGETS.items():
            with self.subTest(skill=name):
                text = (ROOT / "skills" / name / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                self.assertLessEqual(len(text.split()), budget)


if __name__ == "__main__":
    unittest.main()
