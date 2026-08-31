#!/usr/bin/env python3
"""Focused Agent Skills conformance and house-policy tests."""

from __future__ import annotations

import importlib.util
import inspect
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
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
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def write_skill(skill_dir: Path, content: str) -> None:
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


class AgentSkillsConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()

    def validate_spec(self, fixture_name: str) -> list[str]:
        errors: list[str] = []
        self.validator.validate_agent_skill_spec(FIXTURES / fixture_name, errors)
        return errors

    def test_pinned_reference_artifacts_are_present_and_hash_verified(self) -> None:
        self.assertEqual(self.validator.verify_vendored_artifacts(), [])
        self.assertEqual(
            self.validator.AGENT_SKILLS_SPEC_REVISION,
            "69ef37e9424c0a7ea9dd2293b559e43ec8176379",
        )
        self.assertEqual(self.validator.SKILLS_REF_VERSION, "0.1.0")

    def test_vendored_checkout_attributes_preserve_pinned_bytes(self) -> None:
        text_paths = sorted(
            {
                "vendor/manifest.json",
                *(f"vendor/{path}" for path in self.validator.EXPECTED_SKILLS_REF_FILES),
                *(f"vendor/{path}" for path in self.validator.EXPECTED_VENDOR_DOCUMENTS),
            }
        )
        wheel_paths = sorted(
            f"vendor/{path}"
            for path in self.validator.EXPECTED_DEPENDENCY_ARTIFACTS
        )
        result = subprocess.run(
            ["git", "check-attr", "text", "eol", "--", *text_paths, *wheel_paths],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        attributes: dict[tuple[str, str], str] = {}
        for line in result.stdout.splitlines():
            path, attribute, value = line.split(": ", 2)
            attributes[(path, attribute)] = value

        for path in text_paths:
            self.assertEqual(attributes[(path, "text")], "set", path)
            self.assertEqual(attributes[(path, "eol")], "lf", path)
        for path in wheel_paths:
            self.assertEqual(attributes[(path, "text")], "unset", path)

    def test_vendored_code_is_not_imported_before_artifact_verification(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            temp_root = Path(temp)
            (temp_root / "scripts").mkdir()
            shutil.copy2(
                ROOT / "scripts" / "validate-skills-repo.py",
                temp_root / "scripts" / "validate-skills-repo.py",
            )
            shutil.copy2(
                ROOT / "scripts" / "shared_conventions.py",
                temp_root / "scripts" / "shared_conventions.py",
            )
            shutil.copytree(ROOT / "vendor", temp_root / "vendor")
            marker = temp_root / "unverified-code-ran"
            shadow_wheel = temp_root / "vendor" / "wheels" / "000-shadow.whl"
            with zipfile.ZipFile(shadow_wheel, "w") as archive:
                archive.writestr(
                    "strictyaml.py",
                    "from pathlib import Path\n"
                    f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
                    "class YAMLError(Exception):\n"
                    "    pass\n",
                )

            result = subprocess.run(
                [sys.executable, str(temp_root / "scripts" / "validate-skills-repo.py")],
                cwd=temp_root,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            marker_existed = marker.exists()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            marker_existed,
            "an unlisted wheel executed before vendored artifacts were verified",
        )

    def test_vendored_imports_do_not_write_bytecode_into_vendor_tree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            temp_root = Path(temp)
            (temp_root / "scripts").mkdir()
            script = temp_root / "scripts" / "validate-skills-repo.py"
            shutil.copy2(ROOT / "scripts" / "validate-skills-repo.py", script)
            shutil.copy2(
                ROOT / "scripts" / "shared_conventions.py",
                temp_root / "scripts" / "shared_conventions.py",
            )
            shutil.copytree(ROOT / "vendor", temp_root / "vendor")
            command = (
                "import runpy, sys; "
                "sys.pycache_prefix = None; "
                f"runpy.run_path({str(script)!r}, run_name='__main__')"
            )

            result = subprocess.run(
                [sys.executable, "-c", command],
                cwd=temp_root,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            generated = [
                path
                for path in (temp_root / "vendor").rglob("*")
                if path.name == "__pycache__" or path.suffix == ".pyc"
            ]

        self.assertEqual(generated, [], result.stdout + result.stderr)

    def test_symlinked_vendor_tree_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            temp_root = Path(temp)
            vendor_root = temp_root / "vendor"
            shutil.copytree(ROOT / "vendor", vendor_root)
            external_wheels = temp_root / "external-wheels"
            (vendor_root / "wheels").rename(external_wheels)
            (vendor_root / "wheels").symlink_to(external_wheels, target_is_directory=True)
            original_root = self.validator.VENDOR_ROOT
            original_manifest = self.validator.SKILLS_REF_MANIFEST
            self.validator.VENDOR_ROOT = vendor_root
            self.validator.SKILLS_REF_MANIFEST = vendor_root / "manifest.json"
            try:
                errors = self.validator.verify_vendored_artifacts()
            finally:
                self.validator.VENDOR_ROOT = original_root
                self.validator.SKILLS_REF_MANIFEST = original_manifest

        self.assertIn("symlink", "\n".join(errors))

    def test_symlinked_vendor_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            temp_root = Path(temp)
            vendor_root = temp_root / "vendor"
            shutil.copytree(ROOT / "vendor", vendor_root)
            manifest_path = vendor_root / "manifest.json"
            external_manifest = temp_root / "manifest.json"
            manifest_path.rename(external_manifest)
            manifest_path.symlink_to(external_manifest)
            original_root = self.validator.VENDOR_ROOT
            original_manifest = self.validator.SKILLS_REF_MANIFEST
            self.validator.VENDOR_ROOT = vendor_root
            self.validator.SKILLS_REF_MANIFEST = manifest_path
            try:
                errors = self.validator.verify_vendored_artifacts()
            finally:
                self.validator.VENDOR_ROOT = original_root
                self.validator.SKILLS_REF_MANIFEST = original_manifest

        self.assertIn("symlink", "\n".join(errors))

    def test_incomplete_vendor_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            vendor_root = Path(temp) / "vendor"
            vendor_root.mkdir(parents=True)
            manifest = {
                "skills_ref": {
                    "revision": self.validator.AGENT_SKILLS_SPEC_REVISION,
                    "version": self.validator.SKILLS_REF_VERSION,
                    "files": {},
                },
                "dependencies": [],
            }
            manifest_path = vendor_root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            original_root = self.validator.VENDOR_ROOT
            original_manifest = self.validator.SKILLS_REF_MANIFEST
            self.validator.VENDOR_ROOT = vendor_root
            self.validator.SKILLS_REF_MANIFEST = manifest_path
            try:
                errors = self.validator.verify_vendored_artifacts()
            finally:
                self.validator.VENDOR_ROOT = original_root
                self.validator.SKILLS_REF_MANIFEST = original_manifest

        self.assertTrue(errors)
        self.assertIn("pinned set", "\n".join(errors))

    def test_vendored_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            vendor_root = Path(temp) / "vendor"
            shutil.copytree(ROOT / "vendor", vendor_root)
            artifact = (
                vendor_root
                / "wheels"
                / "strictyaml-1.7.3-py3-none-any.whl"
            )
            artifact.write_bytes(b"tampered")
            manifest_path = vendor_root / "manifest.json"
            original_root = self.validator.VENDOR_ROOT
            original_manifest = self.validator.SKILLS_REF_MANIFEST
            self.validator.VENDOR_ROOT = vendor_root
            self.validator.SKILLS_REF_MANIFEST = manifest_path
            try:
                errors = self.validator.verify_vendored_artifacts()
            finally:
                self.validator.VENDOR_ROOT = original_root
                self.validator.SKILLS_REF_MANIFEST = original_manifest

        self.assertTrue(any("vendored artifact hash mismatch" in error for error in errors))

    def test_unrecognized_vendor_subtree_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            vendor_root = Path(temp) / "vendor"
            shutil.copytree(ROOT / "vendor", vendor_root)
            unexpected = vendor_root / "unexpected" / "artifact.py"
            unexpected.parent.mkdir()
            unexpected.write_text("untrusted = True\n", encoding="utf-8")
            manifest_path = vendor_root / "manifest.json"
            original_root = self.validator.VENDOR_ROOT
            original_manifest = self.validator.SKILLS_REF_MANIFEST
            self.validator.VENDOR_ROOT = vendor_root
            self.validator.SKILLS_REF_MANIFEST = manifest_path
            try:
                errors = self.validator.verify_vendored_artifacts()
            finally:
                self.validator.VENDOR_ROOT = original_root
                self.validator.SKILLS_REF_MANIFEST = original_manifest

        self.assertIn(
            "vendor/unexpected/artifact.py: unexpected vendored file",
            "\n".join(errors),
        )

    def test_manifest_must_match_pinned_file_set_and_reject_traversal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            vendor_root = Path(temp) / "vendor"
            (vendor_root / "skills_ref" / "src").mkdir(parents=True)
            (vendor_root / "licenses").mkdir()
            (vendor_root / "wheels").mkdir()
            manifest = {
                "skills_ref": {
                    "repository": "https://github.com/agentskills/agentskills.git",
                    "revision": self.validator.AGENT_SKILLS_SPEC_REVISION,
                    "source_url": "https://github.com/agentskills/agentskills/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379/skills-ref",
                    "version": self.validator.SKILLS_REF_VERSION,
                    "license": "Apache-2.0",
                    "license_file": "skills_ref/LICENSE",
                    "files": {
                        "../escape": "0" * 64,
                    },
                },
                "dependencies": [],
            }
            manifest_path = vendor_root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            original_root = self.validator.VENDOR_ROOT
            original_manifest = self.validator.SKILLS_REF_MANIFEST
            self.validator.VENDOR_ROOT = vendor_root
            self.validator.SKILLS_REF_MANIFEST = manifest_path
            try:
                errors = self.validator.verify_vendored_artifacts()
            finally:
                self.validator.VENDOR_ROOT = original_root
                self.validator.SKILLS_REF_MANIFEST = original_manifest

        joined = "\n".join(errors)
        self.assertIn("manifest skills-ref file set does not match", joined)
        self.assertIn("path traversal", joined)

    def test_spec_checks_report_each_invalid_field_without_yaml_coercion(self) -> None:
        errors = self.validate_spec("invalid-field-types")

        joined = "\n".join(errors)
        self.assertIn("Field 'compatibility' must be a non-empty string", joined)
        self.assertIn("Field 'metadata' must be a mapping", joined)
        self.assertIn("Field 'license' must be a string", joined)
        self.assertIn("Field 'allowed-tools' must be a string", joined)

    def test_nested_metadata_is_rejected_as_a_raw_non_string_value(self) -> None:
        errors = self.validate_spec("metadata-entry-types")

        joined = "\n".join(errors)
        self.assertIn("Field 'metadata' values must be strings", joined)

    def test_plain_scalars_remain_strings_under_strictyaml(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp) / "plain-scalars"
            write_skill(
                skill_dir,
                "---\n"
                "name: plain-scalars\n"
                "description: Use when testing plain scalar semantics.\n"
                "compatibility: 42\n"
                "license: true\n"
                "allowed-tools: false\n"
                "metadata:\n"
                "  answer: 42\n"
                "  enabled: true\n"
                "---\n",
            )
            errors: list[str] = []
            frontmatter = self.validator.validate_agent_skill_spec(skill_dir, errors)

        self.assertEqual(errors, [])
        self.assertEqual(frontmatter["compatibility"], "42")
        self.assertEqual(frontmatter["license"], "true")
        self.assertEqual(frontmatter["allowed-tools"], "false")
        self.assertEqual(frontmatter["metadata"], {"answer": "42", "enabled": "true"})

    def test_deep_frontmatter_recursion_is_a_deterministic_spec_error(self) -> None:
        original = self.validator.reference_yaml_load

        def recurse(_: str) -> object:
            raise RecursionError("maximum recursion depth exceeded")

        self.validator.reference_yaml_load = recurse
        try:
            errors: list[str] = []
            self.validator.validate_agent_skill_spec(
                FIXTURES / "house-policy-violations", errors
            )
        finally:
            self.validator.reference_yaml_load = original

        joined = "\n".join(errors)
        self.assertIn("Agent Skills spec", joined)
        self.assertIn("frontmatter exceeds supported nesting depth", joined)

    def test_reference_validator_accepts_a_canonical_skill(self) -> None:
        errors: list[str] = []

        frontmatter = self.validator.validate_agent_skill_spec(
            ROOT / "skills" / "catch-me-up", errors
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(frontmatter)
        self.assertEqual(frontmatter["name"], "catch-me-up")
        self.assertIn(
            str(ROOT / "vendor"),
            str(Path(inspect.getsourcefile(self.validator.reference_validate) or "")),
        )

    def test_missing_required_fields_are_reported_by_reference(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp) / "missing-name"
            write_skill(
                skill_dir,
                "---\n"
                "description: Use when testing required fields.\n"
                "---\n",
            )
            errors: list[str] = []
            self.validator.validate_agent_skill_spec(skill_dir, errors)

        self.assertTrue(
            any("Missing required field in frontmatter: name" in error for error in errors)
        )

    def test_reference_limits_are_reported(self) -> None:
        errors = self.validate_spec("overlong-values")

        joined = "\n".join(errors)
        self.assertIn("Description exceeds 1024 character limit", joined)
        self.assertIn("Compatibility exceeds 500 character limit", joined)

    def test_reference_unexpected_fields_are_reported(self) -> None:
        errors = self.validate_spec("unsupported-frontmatter")

        self.assertIn("Unexpected fields in frontmatter: tools", "\n".join(errors))

    def test_reference_directory_matching_is_reported(self) -> None:
        errors = self.validate_spec("mismatched-directory")

        self.assertIn(
            "Directory name 'mismatched-directory' must match skill name 'declared-name'",
            "\n".join(errors),
        )

    def test_reference_name_rules_are_reported(self) -> None:
        errors = self.validate_spec("invalid-name")

        joined = "\n".join(errors)
        self.assertIn("must be lowercase", joined)
        self.assertIn("cannot start or end with a hyphen", joined)
        self.assertIn("cannot contain consecutive hyphens", joined)
        self.assertIn("contains invalid characters", joined)

    def test_reference_malformed_frontmatter_is_reported(self) -> None:
        errors = self.validate_spec("malformed-frontmatter")

        joined = "\n".join(errors)
        self.assertIn("Agent Skills spec", joined)
        self.assertIn("Invalid YAML in frontmatter", joined)

    def test_exact_uppercase_skill_file_is_a_spec_requirement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp) / "lowercase-file"
            skill_dir.mkdir()
            (skill_dir / "skill.md").write_text(
                "---\n"
                "name: lowercase-file\n"
                "description: Use when testing exact skill files.\n"
                "---\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            result = self.validator.validate_agent_skill_spec(skill_dir, errors)

        self.assertIsNone(result)
        self.assertIn("missing required file: SKILL.md", "\n".join(errors))

    def test_regular_skill_path_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_path = Path(temp) / "skills" / "example"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text("not a directory", encoding="utf-8")
            errors: list[str] = []

            result = self.validator.validate_agent_skill_spec(skill_path, errors)

        self.assertIsNone(result)
        self.assertIn("must be a directory", "\n".join(errors))

    def test_regular_skills_root_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            temp_root = Path(temp)
            (temp_root / "skills").write_text("not a directory", encoding="utf-8")
            original_root = self.validator.ROOT
            original_skills_dir = self.validator.SKILLS_DIR
            self.validator.ROOT = temp_root
            self.validator.SKILLS_DIR = temp_root / "skills"
            errors: list[str] = []
            try:
                names = self.validator.validate_skills(errors)
            finally:
                self.validator.ROOT = original_root
                self.validator.SKILLS_DIR = original_skills_dir

        self.assertEqual(names, [])
        self.assertIn("skills/: must be a directory", "\n".join(errors))

    def test_name_whitespace_is_not_trimmed_into_validity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp) / "skill"
            write_skill(
                skill_dir,
                "---\n"
                "name: ' skill '\n"
                "description: Use when testing exact skill names.\n"
                "license: MIT\n"
                "---\n",
            )
            errors: list[str] = []
            self.validator.validate_agent_skill_spec(skill_dir, errors)

        joined = "\n".join(errors)
        self.assertIn("must not have leading or trailing whitespace", joined)
        self.assertIn("contains invalid characters", joined)
        self.assertIn("Directory name 'skill' must match skill name ' skill '", joined)

    def test_skill_names_reject_unicode_and_nfkc_lookalikes(self) -> None:
        for name in ("café", "ｔｅｓｔ"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                prefix="skill-validation-"
            ) as temp:
                skill_dir = Path(temp) / name
                write_skill(
                    skill_dir,
                    "---\n"
                    f"name: {name}\n"
                    "description: Use when testing portable skill names.\n"
                    "license: MIT\n"
                    "---\n",
                )
                errors: list[str] = []
                self.validator.validate_agent_skill_spec(skill_dir, errors)

            self.assertIn(
                "must match the portable ASCII name grammar",
                "\n".join(errors),
            )

    def test_reference_parser_matches_comments_quotes_and_block_scalars(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_file = Path(temp) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: reference-parser\n"
                "description: 'Use O''Reilly # literally.' # trailing\n"
                "compatibility: \"" + chr(92) + "N\" # YAML escape\n"
                "license: MIT # SPDX identifier\n"
                "---\n",
                encoding="utf-8",
            )
            frontmatter, parse_error = self.validator.parse_frontmatter(skill_file)

        self.assertIsNone(parse_error)
        self.assertEqual(
            frontmatter,
            {
                "name": "reference-parser",
                "description": "Use O'Reilly # literally.",
                "compatibility": "\u0085",
                "license": "MIT",
            },
        )

    def test_reference_parser_rejects_flow_mappings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_file = Path(temp) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: reference-flow\n"
                "description: Use when testing reference flow behavior.\n"
                "metadata: {owner: O'Reilly, team: tools}\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )
            frontmatter, parse_error = self.validator.parse_frontmatter(skill_file)

        self.assertEqual(frontmatter, {})
        self.assertIn("Invalid YAML in frontmatter", parse_error or "")

    def test_reference_parser_rejects_unknown_double_quote_escapes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_file = Path(temp) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: reference-escape\n"
                "description: \"Use when testing unknown escapes.\"\n"
                "compatibility: \"Use " + chr(92) + "q\"\n"
                "license: MIT\n"
                "---\n",
                encoding="utf-8",
            )
            frontmatter, parse_error = self.validator.parse_frontmatter(skill_file)

        self.assertEqual(frontmatter, {})
        self.assertIn("Invalid YAML in frontmatter", parse_error or "")

    def test_frontmatter_delimiters_must_be_standalone_lines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp) / "delimiter-probe"
            write_skill(
                skill_dir,
                "---\n"
                "name: delimiter-probe\n"
                "license: MIT\n"
                "description: Use when foo---bar is present.\n"
                "tools: forbidden\n"
                "---\n",
            )
            frontmatter, parse_error = self.validator.parse_frontmatter(
                skill_dir / "SKILL.md"
            )
            errors: list[str] = []
            self.validator.validate_agent_skill_spec(skill_dir, errors)

        self.assertIsNone(parse_error)
        self.assertEqual(
            frontmatter.get("description"),
            "Use when foo---bar is present.",
        )
        self.assertEqual(frontmatter.get("tools"), "forbidden")
        self.assertIn("Unexpected fields in frontmatter: tools", "\n".join(errors))

    def test_reference_block_scalar_indicators_and_chomping(self) -> None:
        expected = {
            ">": "first\nsecond\n",
            ">-": "first\nsecond",
            ">+": "first\nsecond\n",
            "|": "first\n\nsecond\n",
            "|-": "first\n\nsecond",
            "|+": "first\n\nsecond\n",
            "|2": "first\n\nsecond\n",
            "|+2": "first\n\nsecond\n",
            "|2+": "first\n\nsecond\n",
            ">2": "first\nsecond\n",
        }
        for indicator, value in expected.items():
            with self.subTest(indicator=indicator), tempfile.TemporaryDirectory(
                prefix="skill-validation-"
            ) as temp:
                skill_file = Path(temp) / "SKILL.md"
                skill_file.write_text(
                    "---\n"
                    "name: block-indicator\n"
                    f"description: {indicator}\n"
                    "  first\n"
                    "\n"
                    "  second\n"
                    "license: MIT\n"
                    "---\n",
                    encoding="utf-8",
                )
                frontmatter, parse_error = self.validator.parse_frontmatter(skill_file)

            self.assertIsNone(parse_error)
            self.assertEqual(frontmatter["description"], value)

    def test_reference_block_scalar_headers_accept_outside_comments(self) -> None:
        for indicator in (">", "|"):
            with self.subTest(indicator=indicator), tempfile.TemporaryDirectory(
                prefix="skill-validation-"
            ) as temp:
                skill_file = Path(temp) / "SKILL.md"
                skill_file.write_text(
                    "---\n"
                    "name: block-comment\n"
                    f"description: {indicator} # comment\n"
                    "  Use when testing block comments.\n"
                    "license: MIT\n"
                    "---\n",
                    encoding="utf-8",
                )
                frontmatter, parse_error = self.validator.parse_frontmatter(skill_file)

            self.assertIsNone(parse_error)
            self.assertEqual(
                frontmatter["description"], "Use when testing block comments.\n"
            )

    def test_metadata_scalar_coercion_matches_reference_behavior(self) -> None:
        frontmatter, parse_error = self.validator.parse_frontmatter(
            FIXTURES / "metadata-entry-types" / "SKILL.md"
        )

        self.assertIsNone(parse_error)
        self.assertEqual(
            frontmatter["metadata"],
            {"7": "value", "owner": "42", "nested": "{'team': 'platform'}"},
        )

    def test_canonical_skills_are_each_traversed_once(self) -> None:
        calls: list[Path] = []
        original = self.validator.validate_agent_skill_spec

        def record(path: Path, errors: list[str]) -> dict[object, object] | None:
            calls.append(path)
            return original(path, errors)

        self.validator.validate_agent_skill_spec = record
        errors: list[str] = []
        canonical_names = self.validator.validate_skills(errors)

        expected = {ROOT / "skills" / name for name in canonical_names}
        self.assertEqual(calls, sorted(expected))
        self.assertEqual(errors, [])

    def test_scenario_convention_covers_non_exempt_canonical_skills(self) -> None:
        self.assertEqual(
            self.validator.VALIDATION_SCENARIO_EXEMPTIONS,
            {"pr-generator", "testflight-notes"},
        )
        for skill_dir in sorted(
            path for path in (ROOT / "skills").iterdir() if path.is_dir()
        ):
            if skill_dir.name in self.validator.VALIDATION_SCENARIO_EXEMPTIONS:
                continue
            with self.subTest(skill=skill_dir.name):
                errors: list[str] = []
                self.validator.validate_validation_scenarios(skill_dir, errors)
                self.assertEqual(errors, [])

    def test_commit_message_binds_approval_to_commit_parent_and_tree(self) -> None:
        skill_text = (ROOT / "skills" / "commit-message" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        draft_tree = skill_text.index("git write-tree")
        recheck = skill_text.index("### 6) Re-check and commit")
        commit = skill_text.index("git commit -F")

        self.assertLess(draft_tree, recheck)
        self.assertLess(recheck, commit)
        self.assertIn("draft_parent", skill_text)
        self.assertIn("draft_base_tree", skill_text)
        self.assertIn("normal/unborn procedure", skill_text)
        self.assertIn("current_parent", skill_text)
        self.assertIn('[ "$current_parent" != "$draft_parent" ]', skill_text)
        self.assertIn("commit parent or staged tree changed", skill_text.lower())

    def test_commit_message_drafts_only_from_recorded_parent_and_tree(self) -> None:
        skill_text = (ROOT / "skills" / "commit-message" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        evidence_start = skill_text.index("### 1) Collect evidence")
        commit_start = skill_text.index("### 6) Re-check and commit")
        evidence_text = skill_text[evidence_start:commit_start]

        self.assertIn(
            'git --no-pager diff --no-ext-diff "$draft_base_tree" "$staged_tree" "$@"',
            evidence_text,
        )
        for evidence_call in (
            "run_git_evidence --name-only",
            "run_git_evidence --stat",
            "run_git_evidence",
            "run_git_evidence --name-status",
        ):
            with self.subTest(call=evidence_call):
                self.assertIn(f"{evidence_call} || exit $?", evidence_text)
        for live_index_evidence in (
            "git --no-pager diff --cached --name-only",
            "git --no-pager diff --cached --stat",
            "git --no-pager diff --cached\n",
        ):
            with self.subTest(command=live_index_evidence):
                self.assertNotIn(live_index_evidence, evidence_text)

    def test_commit_message_supports_unborn_initial_commit_identity(self) -> None:
        skill_text = (ROOT / "skills" / "commit-message" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("git rev-parse --verify HEAD", skill_text)
        self.assertIn("git symbolic-ref --quiet HEAD", skill_text)
        self.assertIn("git show-ref --verify --quiet", skill_text)
        self.assertIn("git mktree </dev/null", skill_text)
        self.assertIn("unborn:<ref>", skill_text)
        self.assertIn("draft_base_tree", skill_text)
        self.assertIn("transition from an unborn parent", skill_text.lower())

    def test_commit_message_scenarios_cover_parent_and_aba_drift(self) -> None:
        scenario_text = (
            ROOT
            / "skills"
            / "commit-message"
            / "references"
            / "validation-scenarios.md"
        ).read_text(encoding="utf-8").lower()

        for marker in (
            "commit-parent drift",
            "unchanged staged tree",
            "aba",
            "recorded parent",
            "recorded staged tree",
            "unborn initial commit",
            "empty tree",
            "evidence read failure",
            "explicitly exit",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, scenario_text)

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

    def test_validation_scenario_labels_are_unique_and_ignore_fenced_labels(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp)
            references_dir = skill_dir / "references"
            references_dir.mkdir()
            (references_dir / "validation-scenarios.md").write_text(
                "# Validation Scenarios\n\n"
                "## Scenario 1: Happy path\n"
                "Setup: a repository is available\n"
                "Prompt: Use the skill on the repository.\n"
                "Pass:\n"
                "```text\n"
                "Pass: this example must not satisfy the real section.\n"
                "`````\n\n"
                "## Scenario 2: Edge case\n"
                "Setup: an edge case is available\n"
                "Setup: a duplicate label is present\n"
                "Prompt: Use the skill for the edge case.\n"
                "Pass: the edge case is handled.\n\n"
                "## Scenario 3: Adversarial\n"
                "Setup: adversarial input is available\n"
                "Prompt: Use the skill for adversarial input.\n"
                "Pass: the input is handled safely.\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            self.validator.validate_validation_scenarios(skill_dir, errors)

        joined = "\n".join(errors)
        self.assertIn("Scenario 1: Pass content must be non-empty", joined)
        self.assertIn("Scenario 2: duplicate Setup label", joined)

    def test_validation_scenario_categories_require_distinct_headings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp)
            references_dir = skill_dir / "references"
            references_dir.mkdir()
            (references_dir / "validation-scenarios.md").write_text(
                "# Validation Scenarios\n\n"
                "## Scenario 1: Happy path / edge case / adversarial\n"
                "Setup: a repository is available\n"
                "Prompt: Use the skill on the repository.\n"
                "Pass: the skill handles the repository.\n\n"
                "## Scenario 2: Alternate input\n"
                "Setup: alternate input is available\n"
                "Prompt: Use the skill for alternate input.\n"
                "Pass: the alternate input is handled.\n\n"
                "## Scenario 3: Another input\n"
                "Setup: another input is available\n"
                "Prompt: Use the skill for another input.\n"
                "Pass: the other input is handled safely.\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            self.validator.validate_validation_scenarios(skill_dir, errors)

        self.assertIn(
            "must associate happy path, edge case, and adversarial coverage "
            "with distinct scenario headings",
            "\n".join(errors),
        )

    def test_validation_scenario_headings_inside_fences_do_not_count(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp)
            references_dir = skill_dir / "references"
            references_dir.mkdir()
            (references_dir / "validation-scenarios.md").write_text(
                "# Validation Scenarios\n\n"
                "## Scenario 1: Happy path\n"
                "Setup: a repository is available\n"
                "Prompt: Use the skill on the repository.\n"
                "Pass: the skill handles the repository.\n\n"
                "## Scenario 2: Edge case\n"
                "Setup: an edge case is available\n"
                "Prompt: Use the skill for the edge case.\n"
                "Pass: the edge case is handled.\n\n"
                "```markdown\n"
                "## Scenario 3: Adversarial\n"
                "Setup: this is only an example\n"
                "Prompt: this is only an example\n"
                "Pass: this is only an example\n"
                "```\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            self.validator.validate_validation_scenarios(skill_dir, errors)

        joined = "\n".join(errors)
        self.assertIn("must define at least 3 scenarios", joined)
        self.assertIn("must include a adversarial scenario", joined)

    def test_scenarios_inside_html_comments_do_not_count(self) -> None:
        wrappers = (
            ("<!--\n", "-->\n"),
            ("\\\\<!--\n", "-->\n"),
        )
        for opening, closing in wrappers:
            with self.subTest(opening=opening), tempfile.TemporaryDirectory(
                prefix="skill-validation-"
            ) as temp:
                skill_dir = Path(temp)
                references_dir = skill_dir / "references"
                references_dir.mkdir()
                (references_dir / "validation-scenarios.md").write_text(
                    "# Validation Scenarios\n\n"
                    + opening
                    + "## Scenario 1: Happy path\n"
                    "Setup: a repository is available\n"
                    "Prompt: Use the skill on the repository.\n"
                    "Pass: the skill handles the repository.\n\n"
                    "## Scenario 2: Edge case\n"
                    "Setup: an edge case is available\n"
                    "Prompt: Use the skill for the edge case.\n"
                    "Pass: the edge case is handled.\n\n"
                    "## Scenario 3: Adversarial\n"
                    "Setup: adversarial input is available\n"
                    "Prompt: Use the skill for adversarial input.\n"
                    "Pass: the input is handled safely.\n"
                    + closing,
                    encoding="utf-8",
                )
                errors: list[str] = []
                self.validator.validate_validation_scenarios(skill_dir, errors)

                joined = "\n".join(errors)
                self.assertIn("must define at least 3 scenarios", joined)
                self.assertIn("must include a happy path scenario", joined)
                self.assertIn("must include a edge case scenario", joined)
                self.assertIn("must include a adversarial scenario", joined)

    def test_labels_inside_multiline_inline_code_do_not_count(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp)
            references_dir = skill_dir / "references"
            references_dir.mkdir()
            scenarios = []
            for number, category in enumerate(
                ("Happy path", "Edge case", "Adversarial"), start=1
            ):
                scenarios.append(
                    f"## Scenario {number}: {category}\n"
                    "Example: `literal\n"
                    "Setup: fake setup\n"
                    "Prompt: fake prompt\n"
                    "Pass: fake result\n"
                    "marker`\n"
                )
            (references_dir / "validation-scenarios.md").write_text(
                "# Validation Scenarios\n\n" + "\n".join(scenarios),
                encoding="utf-8",
            )
            errors: list[str] = []
            self.validator.validate_validation_scenarios(skill_dir, errors)

        joined = "\n".join(errors)
        for number in range(1, 4):
            self.assertIn(f"Scenario {number}: missing Setup label", joined)
            self.assertIn(f"Scenario {number}: missing Prompt label", joined)
            self.assertIn(f"Scenario {number}: missing Pass label", joined)

    def test_literal_html_comment_markers_do_not_hide_scenarios(self) -> None:
        prefixes = (
            "```html <!-- literal fence info\n<p>example</p>\n```\n\n",
            "Use the literal marker `<!--` in documentation.\n\n",
            "Use a multiline code span: `literal\ninside <!-- marker`.\n\n",
            "Use the escaped marker \\<!-- in documentation.\n\n",
            "Unmatched ` literal\n\n```md\n` fence content\n```\n\n",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory(
                prefix="skill-validation-"
            ) as temp:
                skill_dir = Path(temp)
                references_dir = skill_dir / "references"
                references_dir.mkdir()
                (references_dir / "validation-scenarios.md").write_text(
                    "# Validation Scenarios\n\n"
                    + prefix
                    + "## Scenario 1: Happy path\n"
                    "Setup: a repository is available\n"
                    "Prompt: Use the skill on the repository.\n"
                    "Pass: the skill handles the repository.\n\n"
                    "## Scenario 2: Edge case\n"
                    "Setup: an edge case is available\n"
                    "Prompt: Use the skill for the edge case.\n"
                    "Pass: the edge case is handled.\n\n"
                    "## Scenario 3: Adversarial\n"
                    "Setup: adversarial input is available\n"
                    "Prompt: Use the skill for adversarial input.\n"
                    "Pass: the input is handled safely.\n",
                    encoding="utf-8",
                )
                errors: list[str] = []
                self.validator.validate_validation_scenarios(skill_dir, errors)

                self.assertEqual(errors, [])

    def test_validation_scenario_categories_require_complete_phrases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            skill_dir = Path(temp)
            references_dir = skill_dir / "references"
            references_dir.mkdir()
            (references_dir / "validation-scenarios.md").write_text(
                "# Validation Scenarios\n\n"
                "## Scenario 1: Unhappy path\n"
                "Setup: a repository is available\n"
                "Prompt: Use the skill on the repository.\n"
                "Pass: the skill handles the repository.\n\n"
                "## Scenario 2: Edge cases\n"
                "Setup: an edge case is available\n"
                "Prompt: Use the skill for the edge case.\n"
                "Pass: the edge case is handled.\n\n"
                "## Scenario 3: Adversarially\n"
                "Setup: adversarial input is available\n"
                "Prompt: Use the skill for adversarial input.\n"
                "Pass: the input is handled safely.\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            self.validator.validate_validation_scenarios(skill_dir, errors)

        joined = "\n".join(errors)
        self.assertIn("must include a happy path scenario", joined)
        self.assertIn("must include a edge case scenario", joined)
        self.assertIn("must include a adversarial scenario", joined)

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

    def test_cross_skill_references_accept_qualified_local_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            temp_root = Path(temp)
            skills_dir = temp_root / "skills"
            write_skill(
                skills_dir / "caller",
                "Use `g0ld2k-skills:callee` for delegated work.\n",
            )
            write_skill(skills_dir / "callee", "# Callee\n")
            original_root = self.validator.ROOT
            original_skills_dir = self.validator.SKILLS_DIR
            self.validator.ROOT = temp_root
            self.validator.SKILLS_DIR = skills_dir
            try:
                errors: list[str] = []
                self.validator.validate_cross_skill_references(
                    ["caller", "callee"], errors
                )
            finally:
                self.validator.ROOT = original_root
                self.validator.SKILLS_DIR = original_skills_dir

        self.assertEqual(errors, [])

    def test_cross_skill_references_reject_unknown_qualified_local_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-validation-") as temp:
            temp_root = Path(temp)
            skills_dir = temp_root / "skills"
            write_skill(
                skills_dir / "caller",
                "Use `g0ld2k-skills:missing` for delegated work.\n",
            )
            original_root = self.validator.ROOT
            original_skills_dir = self.validator.SKILLS_DIR
            self.validator.ROOT = temp_root
            self.validator.SKILLS_DIR = skills_dir
            try:
                errors: list[str] = []
                self.validator.validate_cross_skill_references(["caller"], errors)
            finally:
                self.validator.ROOT = original_root
                self.validator.SKILLS_DIR = original_skills_dir

        self.assertIn(
            "cross-skill reference to unknown skill: g0ld2k-skills:missing",
            "\n".join(errors),
        )


if __name__ == "__main__":
    unittest.main()
