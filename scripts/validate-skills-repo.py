#!/usr/bin/env python3
"""Validate the repository's skill publishing and plugin packaging shape."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from pathlib import PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
LEGACY_SKILLS_DIR = ROOT / "Skills"
PACKAGING_DIR = ROOT / "packaging"
PLUGINS_DIR = ROOT / "plugins"
VENDOR_ROOT = ROOT / "vendor"
SKILLS_REF_SOURCE_DIR = VENDOR_ROOT / "skills_ref" / "src"
SKILLS_REF_MANIFEST = VENDOR_ROOT / "manifest.json"
PLUGIN_SCHEMA_URL = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PLUGIN_SCHEMA_PATH = ROOT / "schemas" / "agent-plugins" / "1.0.0" / "plugin.schema.json"
EXPLICIT_ONLY_SKILLS = {
    "integration-branch-orchestrator",
    "work-request-orchestration",
}
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RETIRED_SKILL_NAMES = {"codex-pr-approval-loop"}
EXTERNAL_SKILL_PREFIXES = ("superpowers:",)
AGENT_SKILLS_SPEC_URL = "https://agentskills.io/specification"
AGENT_SKILLS_SPEC_REVISION = "69ef37e9424c0a7ea9dd2293b559e43ec8176379"
SKILLS_REF_VERSION = "0.1.0"
VALIDATION_SCENARIO_PATH = Path("references") / "validation-scenarios.md"
VALIDATION_SCENARIO_EXEMPTIONS = {
    "commit-message",
    "pr-generator",
    "testflight-notes",
}
NON_SKILL_TOKENS = {"gh", "git", "jq", "rg", "make", "mktemp", "shellcheck"}
SKILL_REF_CONTEXT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:[Uu]se|[Ii]nvoke|[Dd]elegat\w+ to|[Rr]un)\s+\x60([a-z0-9][a-z0-9:-]*[a-z0-9])\x60"
)
COMPANION_REF_RE = re.compile(
    r"^\s*-\s+\x60([a-z0-9][a-z0-9:-]*[a-z0-9])\x60\s+(?:for|to|when|before|after)\b",
    re.MULTILINE,
)
SCENARIO_MARKUP_TOKEN_RE = re.compile(r"<!--|`+")
INLINE_BLOCK_BOUNDARY_RE = re.compile(
    r"^ {0,3}(?:`{3,}|~{3,}|#{1,6}(?:[ \t]+|$)|<!--)"
)


def exact_child(parent: Path, name: str) -> Path | None:
    if not parent.is_dir():
        return None
    return next((child for child in parent.iterdir() if child.name == name), None)


def has_exact_child(parent: Path, name: str) -> bool:
    return exact_child(parent, name) is not None


def exact_skill_file(skill_dir: Path) -> Path | None:
    """Return SKILL.md only when its filename casing is exact."""
    return exact_child(skill_dir, "SKILL.md")


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _vendor_path_error(path: Path, label: str) -> str | None:
    """Return an error when a vendored path escapes or crosses a symlink."""
    try:
        relative = path.relative_to(VENDOR_ROOT)
    except ValueError:
        return f"{path}: vendored {label} must remain inside {VENDOR_ROOT}"

    current = VENDOR_ROOT
    if current.is_symlink():
        return f"{current}: symlinks are not allowed in vendored paths"
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return f"{current}: symlinks are not allowed in vendored paths"
    return None


def _manifest(errors: list[str]) -> dict[str, object] | None:
    path_error = _vendor_path_error(SKILLS_REF_MANIFEST, "manifest")
    if path_error:
        errors.append(path_error)
        return None
    try:
        manifest = json.loads(SKILLS_REF_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return manifest if isinstance(manifest, dict) else None


# These values are the validator's trust anchor.  The manifest is useful
# provenance/documentation, but cannot change which code or dependencies are
# eligible for import.
EXPECTED_SKILLS_REF_FILES: dict[str, str] = {
    "skills_ref/LICENSE": "58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd",
    "licenses/python-dateutil-LICENSE.txt": "ba00f51a0d92823b5a1cde27d8b5b9d2321e67ed8da9bc163eff96d5e17e577e",
    "licenses/six-LICENSE.txt": "4375ba20e2b9c6c4e7cad2940a628fd90e95cc3d50ee92aae755715d8ba1fbd0",
    "licenses/strictyaml-LICENSE.txt": "288b0b2d89e16908047eb4d8b37c03da5895808920deddc381ae02b319f79d19",
    "skills_ref/src/skills_ref/__init__.py": "a3da705c4847ac19c016f67e3a6c56a94e160986a823d148c21dca4c9b312b4a",
    "skills_ref/src/skills_ref/errors.py": "dd4570964e82d7c8f57e76dd3a1e9e593e1530f22e36e633e8eadb9bd05d36f3",
    "skills_ref/src/skills_ref/models.py": "c6645fcfc04c78e773657856e8c6058e43951ce283e9b303ca721df1acac6a7b",
    "skills_ref/src/skills_ref/parser.py": "9a74c9a90eb217b82bec27570332eab74547acfbee2973c0a8bcd23f6c7bc211",
    "skills_ref/src/skills_ref/prompt.py": "8ed90a61685b84050a8fde32e63d5f3f04c205b05bfc5f8ef4bb2f101cc9cf15",
    "skills_ref/src/skills_ref/validator.py": "b5ee3d8537c83c959c31c2cb080a5227646ede5aea545f1ac835ed3c4645f6c5",
}
EXPECTED_DEPENDENCY_ARTIFACTS: dict[str, dict[str, str]] = {
    "wheels/strictyaml-1.7.3-py3-none-any.whl": {
        "name": "strictyaml",
        "version": "1.7.3",
        "url": "https://files.pythonhosted.org/packages/96/7c/a81ef5ef10978dd073a854e0fa93b5d8021d0594b639cc8f6453c3c78a1d/strictyaml-1.7.3-py3-none-any.whl",
        "sha256": "fb5c8a4edb43bebb765959e420f9b3978d7f1af88c80606c03fb420888f5d1c7",
        "license": "MIT",
        "license_file": "strictyaml-1.7.3.dist-info/LICENSE.txt",
    },
    "wheels/python_dateutil-2.9.0.post0-py2.py3-none-any.whl": {
        "name": "python-dateutil",
        "version": "2.9.0.post0",
        "url": "https://files.pythonhosted.org/packages/ec/57/56b9bcc3c9c6a792fcbaf139543cee77261f3651ca9da0c93f5c1221264b/python_dateutil-2.9.0.post0-py2.py3-none-any.whl",
        "sha256": "a8b2bc7bffae282281c8140a97d3aa9c14da0b136dfe83f850eea9a5f7470427",
        "license": "Apache-2.0 OR BSD-3-Clause",
        "license_file": "python_dateutil-2.9.0.post0.dist-info/LICENSE",
    },
    "wheels/six-1.17.0-py2.py3-none-any.whl": {
        "name": "six",
        "version": "1.17.0",
        "url": "https://files.pythonhosted.org/packages/b7/ce/149a00dd41f10bc29e5921b496af8b574d8413afcd5e30dfa0ed46c2cc5e/six-1.17.0-py2.py3-none-any.whl",
        "sha256": "4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274",
        "license": "MIT",
        "license_file": "six-1.17.0.dist-info/LICENSE",
    },
}
EXPECTED_VENDOR_FILES = {
    "skills_ref": frozenset(
        path.removeprefix("skills_ref/")
        for path in EXPECTED_SKILLS_REF_FILES
        if path.startswith("skills_ref/")
    ),
    "licenses": frozenset(
        path.removeprefix("licenses/")
        for path in EXPECTED_SKILLS_REF_FILES
        if path.startswith("licenses/")
    ),
    "wheels": frozenset(
        path.removeprefix("wheels/") for path in EXPECTED_DEPENDENCY_ARTIFACTS
    ),
}
EXPECTED_SOURCE_PROVENANCE = {
    "repository": "https://github.com/agentskills/agentskills.git",
    "revision": AGENT_SKILLS_SPEC_REVISION,
    "source_url": "https://github.com/agentskills/agentskills/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379/skills-ref",
    "version": SKILLS_REF_VERSION,
    "license": "Apache-2.0",
    "license_file": "skills_ref/LICENSE",
}
EXPECTED_MANIFEST_KEYS = frozenset({"skills_ref", "dependencies"})
EXPECTED_SOURCE_KEYS = frozenset({*EXPECTED_SOURCE_PROVENANCE, "files"})
EXPECTED_DEPENDENCY_KEYS = frozenset(
    {"name", "version", "url", "path", "sha256", "license", "license_file"}
)


def _is_safe_manifest_path(relative: str) -> bool:
    """Accept only normalized, relative POSIX paths inside vendor/."""
    if not relative or "\\" in relative:
        return False
    path = PurePosixPath(relative)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def _vendor_files(relative_root: str) -> set[str]:
    root = VENDOR_ROOT / relative_root
    if not root.is_dir():
        return set()
    files: set[str] = set()
    for path in root.rglob("*"):
        if path.is_file() or path.is_symlink():
            files.add(path.relative_to(root).as_posix())
    return files


def _hash_file(path: Path, errors: list[str], label: str) -> str | None:
    path_error = _vendor_path_error(path, label)
    if path_error:
        errors.append(path_error)
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        errors.append(f"{path}: cannot verify vendored {label}: {exc}")
        return None


def verify_vendored_artifacts() -> list[str]:
    """Verify the pinned reference source and dependency archives before use."""
    errors: list[str] = []
    manifest = _manifest(errors)
    if manifest is None:
        if not errors:
            errors.append(f"{SKILLS_REF_MANIFEST}: missing or invalid vendored manifest")
        return errors

    if set(manifest) != EXPECTED_MANIFEST_KEYS:
        errors.append(
            "vendor/manifest.json: manifest entries do not match pinned set "
            f"{sorted(EXPECTED_MANIFEST_KEYS)}"
        )

    source = manifest.get("skills_ref")
    if not isinstance(source, dict):
        errors.append("vendor/manifest.json: missing skills_ref provenance")
    else:
        if set(source) != EXPECTED_SOURCE_KEYS:
            errors.append(
                "vendor/manifest.json: skills-ref provenance entries do not match pinned set"
            )
        for key, expected in EXPECTED_SOURCE_PROVENANCE.items():
            if source.get(key) != expected:
                errors.append(f"vendor/manifest.json: skills-ref {key} is not pinned")
        source_files = source.get("files")
        if not isinstance(source_files, dict):
            errors.append("vendor/manifest.json: missing skills-ref file hashes")
        else:
            for relative in source_files:
                if not isinstance(relative, str):
                    errors.append("vendor/manifest.json: invalid skills-ref file hash entry")
                elif not _is_safe_manifest_path(relative):
                    errors.append(
                        f"vendor/manifest.json: path traversal in skills-ref file path: {relative}"
                    )
            if set(source_files) != set(EXPECTED_SKILLS_REF_FILES):
                errors.append(
                    "vendor/manifest.json: manifest skills-ref file set does not match pinned set"
                )
            for relative, expected in EXPECTED_SKILLS_REF_FILES.items():
                if source_files.get(relative) != expected:
                    errors.append(
                        f"vendor/manifest.json: skills-ref hash is not pinned for {relative}"
                    )

    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, list):
        errors.append("vendor/manifest.json: missing dependency artifact hashes")
    else:
        manifest_dependencies: dict[str, dict[str, object]] = {}
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                errors.append("vendor/manifest.json: invalid dependency artifact entry")
                continue
            relative = dependency.get("path")
            if not isinstance(relative, str):
                errors.append("vendor/manifest.json: invalid dependency artifact hash entry")
                continue
            if not _is_safe_manifest_path(relative):
                errors.append(
                    f"vendor/manifest.json: path traversal in dependency path: {relative}"
                )
                continue
            if relative in manifest_dependencies:
                errors.append(f"vendor/manifest.json: duplicate dependency path: {relative}")
            manifest_dependencies[relative] = dependency
        if set(manifest_dependencies) != set(EXPECTED_DEPENDENCY_ARTIFACTS):
            errors.append(
                "vendor/manifest.json: manifest dependency entries do not match pinned set"
            )
        for relative, expected in EXPECTED_DEPENDENCY_ARTIFACTS.items():
            dependency = manifest_dependencies.get(relative)
            if dependency is None:
                continue
            if set(dependency) != EXPECTED_DEPENDENCY_KEYS:
                errors.append(
                    f"vendor/manifest.json: dependency entries do not match pinned set for {relative}"
                )
            for key, expected_value in expected.items():
                if dependency.get(key) != expected_value:
                    errors.append(
                        f"vendor/manifest.json: dependency {key} is not pinned for {relative}"
                    )

    for tree, expected_files in EXPECTED_VENDOR_FILES.items():
        actual_files = _vendor_files(tree)
        for unexpected in sorted(actual_files - expected_files):
            errors.append(f"vendor/{tree}/{unexpected}: unexpected vendored file")
        for missing in sorted(expected_files - actual_files):
            errors.append(f"vendor/{tree}/{missing}: missing vendored file")

    # Hash only code/artifacts named by the validator's fixed allowlist. This
    # happens after all manifest paths have been checked for traversal.
    for relative, expected in EXPECTED_SKILLS_REF_FILES.items():
        actual = _hash_file(VENDOR_ROOT / relative, errors, "file")
        if actual is not None and actual != expected:
            errors.append(f"{VENDOR_ROOT / relative}: vendored file hash mismatch")
    for relative, metadata in EXPECTED_DEPENDENCY_ARTIFACTS.items():
        actual = _hash_file(VENDOR_ROOT / relative, errors, "artifact")
        if actual is not None and actual != metadata["sha256"]:
            errors.append(f"{VENDOR_ROOT / relative}: vendored artifact hash mismatch")
    return errors


VENDORED_ARTIFACTS = tuple(EXPECTED_DEPENDENCY_ARTIFACTS.values())


def _vendor_import_paths() -> None:
    """Add only verified, exact paths to the import search path."""
    paths = [VENDOR_ROOT / relative for relative in EXPECTED_DEPENDENCY_ARTIFACTS]
    paths.append(SKILLS_REF_SOURCE_DIR)
    for path in reversed(paths):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)


_REFERENCE_IMPORT_ERROR: str | None = None
reference_validate = None
reference_validate_metadata = None
reference_yaml_load = None
_VENDOR_VERIFICATION_ERRORS = verify_vendored_artifacts()
if not _VENDOR_VERIFICATION_ERRORS:
    # A normal source import writes __pycache__ beside skills_ref. That would
    # mutate the exact vendored tree and make the post-import repository check
    # fail on runners without an external pycache prefix.
    sys.dont_write_bytecode = True
    _vendor_import_paths()
    try:
        from skills_ref import validate as reference_validate
        from skills_ref.parser import strictyaml as reference_strictyaml
        from skills_ref.validator import validate_metadata as reference_validate_metadata

        reference_yaml_load = reference_strictyaml.load
    except Exception as exc:  # pragma: no cover - exercised by missing-artifact gate
        reference_validate = None
        reference_validate_metadata = None
        reference_yaml_load = None
        _REFERENCE_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def _frontmatter_payload(text: str) -> tuple[str | None, str | None]:
    """Extract frontmatter using only standalone delimiter lines."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None, "SKILL.md must start with YAML frontmatter (---)"
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            return "".join(lines[1:index]), None
    return None, "SKILL.md frontmatter not properly closed with ---"


def _parse_frontmatter_data(
    path: Path,
) -> tuple[dict[object, object], dict[object, object], str | None]:
    """Return normalized and raw StrictYAML frontmatter from one skill file."""
    if _VENDOR_VERIFICATION_ERRORS:
        return (
            {},
            {},
            "vendored skills-ref unavailable: " + "; ".join(_VENDOR_VERIFICATION_ERRORS),
        )
    if reference_yaml_load is None:
        return {}, {}, f"vendored skills-ref import failed: {_REFERENCE_IMPORT_ERROR}"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, {}, f"cannot read SKILL.md: {exc}"
    frontmatter_text, delimiter_error = _frontmatter_payload(text)
    if delimiter_error:
        return {}, {}, delimiter_error
    assert frontmatter_text is not None
    try:
        raw_data = reference_yaml_load(frontmatter_text).data
    except RecursionError:
        return {}, {}, "SKILL.md frontmatter exceeds supported nesting depth"
    except Exception as exc:
        return {}, {}, f"Invalid YAML in frontmatter: {exc}"
    if not isinstance(raw_data, dict):
        return {}, {}, "SKILL.md frontmatter must be a YAML mapping"

    # Match skills-ref's only post-parse normalization while retaining the raw
    # mapping for supplemental string-shape checks.
    data = dict(raw_data)
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        data["metadata"] = {str(key): str(value) for key, value in metadata.items()}
    return data, raw_data, None


def parse_frontmatter(path: Path) -> tuple[dict[object, object], str | None]:
    """Parse SKILL.md frontmatter through the pinned skills-ref parser."""
    data, _, error = _parse_frontmatter_data(path)
    if error:
        return {}, error
    return data, None


def parse_openai_yaml(path: Path) -> tuple[dict[str, str], dict[str, object], str | None]:
    if not path.exists():
        return {}, {}, "missing agents/openai.yaml"

    lines = path.read_text(encoding="utf-8").splitlines()
    interface: dict[str, str] = {}
    policy: dict[str, object] = {}
    section: str | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "interface:":
            section = "interface"
            continue
        if stripped == "policy:":
            section = "policy"
            continue
        if section and line.startswith("  ") and ":" in stripped:
            key, _, value = stripped.partition(":")
            parsed_value = strip_quotes(value.strip())
            if parsed_value == "true":
                value_object: object = True
            elif parsed_value == "false":
                value_object = False
            else:
                value_object = parsed_value
            if section == "interface":
                interface[key.strip()] = str(value_object)
            elif section == "policy":
                policy[key.strip()] = value_object

    return interface, policy, None


def is_local_resource_link(target: str) -> bool:
    target = target.strip()
    if (
        not target
        or target.startswith("#")
        or "://" in target
        or target.startswith(("mailto:", "plugin://", "app://", "/"))
    ):
        return False

    path = target.split("#", 1)[0].split("?", 1)[0]
    while path.startswith("./"):
        path = path[2:]
    return path.startswith(("references/", "scripts/", "assets/"))


def validate_local_links(skill_dir: Path, errors: list[str]) -> None:
    for markdown_file in [skill_dir / "SKILL.md", *skill_dir.glob("references/**/*.md")]:
        if not markdown_file.exists():
            continue
        text = markdown_file.read_text(encoding="utf-8")
        for match in LOCAL_LINK_RE.finditer(text):
            target = match.group(1)
            if not is_local_resource_link(target):
                continue
            target_path = target.split("#", 1)[0].split("?", 1)[0]
            if not (skill_dir / target_path).exists():
                rel_file = markdown_file.relative_to(ROOT)
                errors.append(f"{rel_file}: local link does not resolve: {target}")


def load_json(path: Path, errors: list[str]) -> dict[str, object] | None:
    if not path.exists():
        errors.append(f"{path.relative_to(ROOT)}: missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return None


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _spec_error(errors: list[str], skill_file: Path, message: str) -> None:
    errors.append(f"{display_path(skill_file)}: Agent Skills spec: {message}")


def validate_agent_skill_spec(
    skill_dir: Path, errors: list[str]
) -> dict[object, object] | None:
    """Validate one skill with skills-ref, then apply repository identity rules."""
    if not skill_dir.is_dir():
        _spec_error(errors, skill_dir, "skill path must be a directory")
        return None

    skill_file = exact_skill_file(skill_dir)
    if skill_file is None:
        _spec_error(errors, skill_dir / "SKILL.md", "missing required file: SKILL.md")
        return None

    if _VENDOR_VERIFICATION_ERRORS:
        _spec_error(
            errors,
            skill_file,
            "vendored skills-ref unavailable: " + "; ".join(_VENDOR_VERIFICATION_ERRORS),
        )
        return None
    if reference_validate_metadata is None:
        _spec_error(
            errors,
            skill_file,
            f"vendored skills-ref import failed: {_REFERENCE_IMPORT_ERROR}",
        )
        return None

    frontmatter, raw_frontmatter, parse_error = _parse_frontmatter_data(skill_file)
    if parse_error:
        _spec_error(errors, skill_file, parse_error)
        return None

    try:
        reference_errors = reference_validate_metadata(frontmatter, skill_dir)
    except RecursionError:
        _spec_error(errors, skill_file, "frontmatter exceeds supported nesting depth")
        return None
    for message in reference_errors:
        _spec_error(errors, skill_file, message)

    # The pinned demonstration validator omits several final Agent Skills
    # field constraints. Check the raw StrictYAML shapes before skills-ref's
    # metadata normalization stringifies nested values.
    if "license" in raw_frontmatter and not isinstance(
        raw_frontmatter["license"], str
    ):
        _spec_error(errors, skill_file, "Field 'license' must be a string")
    if "compatibility" in raw_frontmatter:
        compatibility = raw_frontmatter["compatibility"]
        if isinstance(compatibility, str) and not compatibility.strip():
            _spec_error(
                errors, skill_file, "Field 'compatibility' must be a non-empty string"
            )
    if "metadata" in raw_frontmatter:
        metadata = raw_frontmatter["metadata"]
        if not isinstance(metadata, dict):
            _spec_error(errors, skill_file, "Field 'metadata' must be a mapping")
        else:
            for key, value in metadata.items():
                if not isinstance(key, str):
                    _spec_error(errors, skill_file, "Field 'metadata' keys must be strings")
                if not isinstance(value, str):
                    _spec_error(errors, skill_file, "Field 'metadata' values must be strings")
    if "allowed-tools" in raw_frontmatter and not isinstance(
        raw_frontmatter["allowed-tools"], str
    ):
        _spec_error(errors, skill_file, "Field 'allowed-tools' must be a string")

    name = frontmatter.get("name")
    if isinstance(name, str) and name.strip():
        if name != name.strip():
            _spec_error(
                errors,
                skill_file,
                "Skill name must not have leading or trailing whitespace",
            )
        if SKILL_NAME_RE.fullmatch(name) is None:
            _spec_error(
                errors,
                skill_file,
                f"Skill name '{name}' contains invalid characters; it must match the portable ASCII name grammar [a-z0-9-].",
            )
        if skill_dir.name != name:
            _spec_error(
                errors,
                skill_file,
                f"Directory name '{skill_dir.name}' must match skill name '{name}'",
            )

    return frontmatter


def _policy_error(errors: list[str], skill_file: Path, message: str) -> None:
    errors.append(f"{display_path(skill_file)}: House policy: {message}")


def validate_house_policies(
    skill_dir: Path, frontmatter: dict[object, object], errors: list[str]
) -> None:
    """Validate choices made by this repository, separate from the spec."""
    skill_file = skill_dir / "SKILL.md"
    description = frontmatter.get("description")
    if isinstance(description, str) and description and not description.startswith("Use when"):
        _policy_error(errors, skill_file, "description must start with 'Use when'")
    if frontmatter.get("license") != "MIT":
        _policy_error(errors, skill_file, "license must be MIT")
    if "allowed-tools" in frontmatter:
        _policy_error(
            errors,
            skill_file,
            "allowed-tools is not permitted by the repository's portability policy",
        )


def _closing_backtick_run_end(
    text: str,
    start: int,
    run_length: int,
    end: int | None = None,
) -> int | None:
    """Return the end of the next exact-length closing backtick run."""
    closing = re.compile(rf"(?<!`)`{{{run_length}}}(?!`)").search(
        text,
        start,
        len(text) if end is None else end,
    )
    if closing is None:
        return None
    return closing.end()


def _is_backslash_escaped(text: str, index: int) -> bool:
    """Return whether punctuation at index follows an odd backslash run."""
    backslash_count = 0
    while index > backslash_count and text[index - backslash_count - 1] == "\\":
        backslash_count += 1
    return backslash_count % 2 == 1


def _find_unescaped_markup_token(text: str, start: int) -> re.Match[str] | None:
    """Return the next unescaped comment marker or backtick run."""
    candidate = SCENARIO_MARKUP_TOKEN_RE.search(text, start)
    while candidate is not None and _is_backslash_escaped(text, candidate.start()):
        next_start = (
            candidate.start() + 1
            if candidate.group(0).startswith("`")
            else candidate.end()
        )
        candidate = SCENARIO_MARKUP_TOKEN_RE.search(text, next_start)
    return candidate


def _blank_markup(text: str) -> str:
    """Blank Markdown syntax while preserving its line boundaries."""
    return "".join(character if character in "\r\n" else " " for character in text)


def _inline_code_limits(text: str, lines: list[str]) -> list[int]:
    """Return the enclosing inline Markdown block end for every line."""
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)

    limits = [len(text)] * len(lines)
    index = 0
    while index < len(lines):
        content = lines[index].rstrip("\r\n")
        if not content.strip() or INLINE_BLOCK_BOUNDARY_RE.match(content):
            limits[index] = offsets[index] + len(lines[index])
            index += 1
            continue

        block_end = index + 1
        while block_end < len(lines):
            content = lines[block_end].rstrip("\r\n")
            if not content.strip() or INLINE_BLOCK_BOUNDARY_RE.match(content):
                break
            block_end += 1
        limit = offsets[block_end] if block_end < len(lines) else len(text)
        for block_index in range(index, block_end):
            limits[block_index] = limit
        index = block_end
    return limits


def _mask_comments_and_inline_code(
    line: str,
    document: str,
    line_offset: int,
    inline_code_limit: int,
    in_comment: bool,
    inline_code_ticks: int,
) -> tuple[str, bool, int]:
    """Blank comments and code spans while preserving line boundaries."""
    masked: list[str] = []
    cursor = 0
    while cursor < len(line):
        if in_comment:
            comment_end = line.find("-->", cursor)
            end = len(line) if comment_end < 0 else comment_end + 3
            masked.append(_blank_markup(line[cursor:end]))
            cursor = end
            if comment_end < 0:
                break
            in_comment = False
            continue

        if inline_code_ticks:
            code_end = _closing_backtick_run_end(
                line, cursor, inline_code_ticks
            )
            end = len(line) if code_end is None else code_end
            masked.append(_blank_markup(line[cursor:end]))
            cursor = end
            if code_end is None:
                break
            inline_code_ticks = 0
            continue

        token = _find_unescaped_markup_token(line, cursor)
        if token is None:
            masked.append(line[cursor:])
            break
        token_start = token.start()
        if token.group(0).startswith("`"):
            run_length = len(token.group(0))
            opening_end = token.end()
            has_closing_run = _closing_backtick_run_end(
                document,
                line_offset + opening_end,
                run_length,
                inline_code_limit,
            )
            masked.append(line[cursor:token_start])
            masked.append(
                _blank_markup(line[token_start:opening_end])
                if has_closing_run is not None
                else line[token_start:opening_end]
            )
            cursor = opening_end
            if has_closing_run is not None:
                inline_code_ticks = run_length
            continue
        masked.append(line[cursor:token_start])
        cursor = token_start
        in_comment = True
    return "".join(masked), in_comment, inline_code_ticks


def _mask_scenario_markup(text: str) -> str:
    """Hide comments, code spans, and fenced structural lookalikes."""
    masked: list[str] = []
    in_fence = False
    in_html_comment = False
    inline_code_ticks = 0
    fence_character = ""
    fence_length = 0
    lines = text.splitlines(keepends=True)
    inline_code_limits = _inline_code_limits(text, lines)
    line_offset = 0
    for line_index, raw_line in enumerate(lines):
        # Fenced content is opaque Markdown: comment-like text in its info
        # string or body must not change the surrounding HTML-comment state.
        if in_fence:
            closing_fence = re.match(
                rf"^ {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*$",
                raw_line.rstrip("\r\n"),
            )
            if closing_fence:
                in_fence = False
            structural_lookalike = closing_fence or re.match(
                r"^\s*## Scenario \d+:", raw_line
            ) or re.match(
                r"^\s*(?:Setup|Prompt|Pass):[ \t]*", raw_line
            )
            masked.append(_blank_markup(raw_line) if structural_lookalike else raw_line)
        elif not in_html_comment and not inline_code_ticks:
            fence = re.match(r"^ {0,3}(`{3,}|~{3,})", raw_line)
            if fence:
                in_fence = True
                fence_character = fence.group(1)[0]
                fence_length = len(fence.group(1))
                masked.append(_blank_markup(raw_line))
            else:
                line, in_html_comment, inline_code_ticks = (
                    _mask_comments_and_inline_code(
                        raw_line,
                        text,
                        line_offset,
                        inline_code_limits[line_index],
                        in_html_comment,
                        inline_code_ticks,
                    )
                )
                masked.append(line)
        else:
            line, in_html_comment, inline_code_ticks = _mask_comments_and_inline_code(
                raw_line,
                text,
                line_offset,
                inline_code_limits[line_index],
                in_html_comment,
                inline_code_ticks,
            )
            masked.append(line)
        line_offset += len(raw_line)
    return "".join(masked)


def validate_validation_scenarios(skill_dir: Path, errors: list[str]) -> None:
    """Require activation/output scenarios for a skill covered by policy."""
    scenario_file = skill_dir / VALIDATION_SCENARIO_PATH
    if not scenario_file.exists():
        _policy_error(
            errors,
            skill_dir / "SKILL.md",
            "missing references/validation-scenarios.md; every skill needs happy path, edge case, and adversarial coverage",
        )
        return
    try:
        text = scenario_file.read_text(encoding="utf-8")
    except OSError as exc:
        _policy_error(errors, scenario_file, f"cannot read validation scenarios: {exc}")
        return
    structural_text = _mask_scenario_markup(text)
    heading_matches = list(
        re.finditer(r"^## Scenario \d+:[^\n]*", structural_text, re.MULTILINE)
    )
    headings = [match.group(0) for match in heading_matches]
    if len(headings) < 3:
        _policy_error(
            errors,
            scenario_file,
            "must define at least 3 scenarios (happy path, edge case, and adversarial)",
        )
    lowered_headings = [heading.lower() for heading in headings]
    category_matches: list[set[int]] = []
    for label in ("happy path", "edge case", "adversarial"):
        phrase = re.compile(rf"(?<!\w){re.escape(label)}(?!\w)")
        matches = {
            index
            for index, heading in enumerate(lowered_headings)
            if phrase.search(heading)
        }
        category_matches.append(matches)
        if not matches:
            _policy_error(errors, scenario_file, f"must include a {label} scenario")
    if all(category_matches):
        happy_matches, edge_matches, adversarial_matches = category_matches
        has_distinct_assignment = any(
            len({happy, edge, adversarial}) == 3
            for happy in happy_matches
            for edge in edge_matches
            for adversarial in adversarial_matches
        )
        if not has_distinct_assignment:
            _policy_error(
                errors,
                scenario_file,
                "must associate happy path, edge case, and adversarial coverage "
                "with distinct scenario headings",
            )

    for index, heading_match in enumerate(heading_matches):
        scenario_number = re.match(r"^## Scenario (\d+):", heading_match.group(0))
        if scenario_number is None:
            continue
        scenario_end = (
            heading_matches[index + 1].start()
            if index + 1 < len(heading_matches)
            else len(structural_text)
        )
        scenario_text = structural_text[heading_match.end() : scenario_end]
        labels = list(
            re.finditer(r"^(Setup|Prompt|Pass):[ \t]*", scenario_text, re.MULTILINE)
        )
        for expected_label in ("Setup", "Prompt", "Pass"):
            label_matches = [
                match for match in labels if match.group(1) == expected_label
            ]
            if not label_matches:
                _policy_error(
                    errors,
                    scenario_file,
                    f"Scenario {scenario_number.group(1)}: missing {expected_label} label",
                )
                continue
            if len(label_matches) > 1:
                _policy_error(
                    errors,
                    scenario_file,
                    f"Scenario {scenario_number.group(1)}: duplicate {expected_label} label",
                )
            label_match = label_matches[0]
            label_end = next(
                (
                    match.start()
                    for match in labels
                    if match.start() > label_match.start()
                ),
                len(scenario_text),
            )
            if not scenario_text[label_match.end() : label_end].strip():
                _policy_error(
                    errors,
                    scenario_file,
                    f"Scenario {scenario_number.group(1)}: {expected_label} content must be non-empty",
                )


def schema_type_matches(value: object, expected: str) -> bool:
    return {
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
    }.get(expected, True)


def schema_error(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{display_path(path)}: schema validation failed: {message}")


def validate_schema_value(
    value: object,
    schema: dict[str, object],
    path: Path,
    errors: list[str],
) -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not schema_type_matches(value, expected_type):
        schema_error(errors, path, f"expected {expected_type}")
        return

    if "const" in schema and value != schema["const"]:
        schema_error(errors, path, f"must equal {schema['const']!r}")

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            schema_error(errors, path, f"must contain at least {min_length} characters")
        max_length = schema.get("maxLength")
        if isinstance(max_length, int) and len(value) > max_length:
            schema_error(errors, path, f"must contain at most {max_length} characters")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.match(pattern, value):
            schema_error(errors, path, "does not match the required pattern")

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for name in required:
                if isinstance(name, str) and name not in value:
                    schema_error(errors, path, f"missing required property '{name}'")

        properties = schema.get("properties", {})
        known_properties = properties if isinstance(properties, dict) else {}
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in known_properties:
                    schema_error(errors, path, f"additional property '{name}'")
        additional_schema = schema.get("additionalProperties")
        for name, child in value.items():
            child_schema = known_properties.get(name)
            if not isinstance(child_schema, dict) and isinstance(additional_schema, dict):
                child_schema = additional_schema
            if isinstance(child_schema, dict):
                validate_schema_value(child, child_schema, path, errors)

    if isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for item in value:
                validate_schema_value(item, item_schema, path, errors)


def validate_portable_manifest(
    manifest: object,
    path: Path,
    errors: list[str],
    schema: dict[str, object] | None = None,
) -> None:
    if schema is None:
        try:
            schema = json.loads(PLUGIN_SCHEMA_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            schema_error(errors, PLUGIN_SCHEMA_PATH, f"cannot load pinned schema: {exc}")
            return
    if not isinstance(schema, dict):
        schema_error(errors, PLUGIN_SCHEMA_PATH, "pinned schema must be an object")
        return
    validate_schema_value(manifest, schema, path, errors)


def load_package_configs(errors: list[str]) -> list[dict[str, object]]:
    configs: list[dict[str, object]] = []
    paths = sorted(PACKAGING_DIR.glob("*.json"))
    if not paths:
        errors.append("packaging/: no plugin package configs found")
        return configs
    for path in paths:
        config = load_json(path, errors)
        if not config:
            continue
        if config.get("name") != path.stem:
            errors.append(f"{path.relative_to(ROOT)}: name must match config filename")
        configs.append(config)
    return sorted(configs, key=lambda config: ("marketplace" not in config, str(config.get("name", ""))))


def skill_dirs() -> list[Path]:
    if not SKILLS_DIR.exists():
        return []
    return sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())


def validate_skills(errors: list[str]) -> list[str]:
    if not has_exact_child(ROOT, "skills"):
        errors.append("skills/: missing")
        return []
    if has_exact_child(ROOT, "Skills"):
        errors.append("Skills/: legacy uppercase skill directory must not exist")
    if (SKILLS_DIR / "_template").exists():
        errors.append("skills/_template/: template skill must not exist")
    if (ROOT / "scripts" / "new-skill.sh").exists():
        errors.append("scripts/new-skill.sh: scaffold helper must not exist")

    names: list[str] = []
    for skill_dir in skill_dirs():
        name = skill_dir.name
        names.append(name)
        skill_file = exact_skill_file(skill_dir)
        if skill_file is None:
            validate_agent_skill_spec(skill_dir, errors)
            continue

        frontmatter = validate_agent_skill_spec(skill_dir, errors)
        if frontmatter is not None:
            validate_house_policies(skill_dir, frontmatter, errors)
            if name not in VALIDATION_SCENARIO_EXEMPTIONS:
                validate_validation_scenarios(skill_dir, errors)

        openai, policy, openai_error = parse_openai_yaml(skill_dir / "agents" / "openai.yaml")
        if openai_error:
            errors.append(f"skills/{name}/agents/openai.yaml: {openai_error}")
        else:
            for key in ("display_name", "short_description", "default_prompt"):
                if not openai.get(key):
                    errors.append(f"skills/{name}/agents/openai.yaml: missing interface.{key}")
            short_description = openai.get("short_description", "")
            if short_description and not 25 <= len(short_description) <= 64:
                errors.append(
                    f"skills/{name}/agents/openai.yaml: short_description must be 25-64 characters"
                )
            default_prompt = openai.get("default_prompt", "")
            if default_prompt and f"${name}" not in default_prompt:
                errors.append(f"skills/{name}/agents/openai.yaml: default_prompt must include ${name}")
            if name in EXPLICIT_ONLY_SKILLS and policy.get("allow_implicit_invocation") is not False:
                errors.append(
                    f"skills/{name}/agents/openai.yaml: policy.allow_implicit_invocation must be false"
                )
            if name not in EXPLICIT_ONLY_SKILLS and "allow_implicit_invocation" in policy:
                errors.append(
                    f"skills/{name}/agents/openai.yaml: policy.allow_implicit_invocation must be absent"
                )

        validate_local_links(skill_dir, errors)

    return names


def validate_cross_skill_references(canonical_names: list[str], errors: list[str]) -> None:
    known = set(canonical_names)
    for markdown_file in sorted(SKILLS_DIR.glob("*/SKILL.md")) + sorted(
        SKILLS_DIR.glob("*/references/**/*.md")
    ):
        text = markdown_file.read_text(encoding="utf-8")
        rel = markdown_file.relative_to(ROOT)
        for retired in RETIRED_SKILL_NAMES:
            if retired in text:
                errors.append(f"{rel}: references retired skill name: {retired}")
        tokens = [m.group(1) for m in SKILL_REF_CONTEXT_RE.finditer(text)]
        tokens += [m.group(1) for m in COMPANION_REF_RE.finditer(text)]
        for token in tokens:
            if token in known:
                continue
            if token.startswith(EXTERNAL_SKILL_PREFIXES):
                continue
            if token in NON_SKILL_TOKENS:
                continue
            errors.append(f"{rel}: cross-skill reference to unknown skill: {token}")


def validate_packaging(
    canonical_skill_names: list[str],
    errors: list[str],
    configs: list[dict[str, object]] | None = None,
) -> None:
    configs = configs if configs is not None else load_package_configs(errors)
    pinned_schema = load_json(PLUGIN_SCHEMA_PATH, errors)
    expected_plugin_names: list[str] = []
    skill_memberships: dict[str, list[str]] = {}

    for config in configs:
        plugin_name = config.get("name")
        if not isinstance(plugin_name, str) or not plugin_name:
            errors.append("packaging/: every package config must have a non-empty name")
            continue
        expected_plugin_names.append(plugin_name)
        config_path = PACKAGING_DIR / f"{plugin_name}.json"
        package_skills = config.get("skills")
        if not isinstance(package_skills, list) or not all(
            isinstance(item, str) for item in package_skills
        ):
            errors.append(f"{config_path.relative_to(ROOT)}: skills must be a string array")
            continue

        for skill in package_skills:
            skill_memberships.setdefault(skill, []).append(plugin_name)
            if not (SKILLS_DIR / skill).exists():
                errors.append(
                    f"{config_path.relative_to(ROOT)}: listed skill missing from skills/: {skill}"
                )

        version = config.get("version")
        plugin_dir = PLUGINS_DIR / plugin_name
        manifest_path = plugin_dir / "plugin.json"
        manifest = load_json(manifest_path, errors)
        if manifest is not None:
            validate_portable_manifest(manifest, manifest_path, errors, pinned_schema)
            if isinstance(manifest, dict):
                if manifest.get("name") != plugin_name:
                    errors.append(f"{manifest_path.relative_to(ROOT)}: name must be {plugin_name}")
                if manifest.get("version") != version:
                    errors.append(f"{manifest_path.relative_to(ROOT)}: version must match package config")

        for legacy_path in [
            plugin_dir / ".claude-plugin" / "plugin.json",
            plugin_dir / ".codex-plugin" / "plugin.json",
        ]:
            if legacy_path.exists():
                errors.append(f"{legacy_path.relative_to(ROOT)}: legacy manifest must not exist")

        generated_skills_dir = plugin_dir / "skills"
        if not generated_skills_dir.exists():
            errors.append(f"{generated_skills_dir.relative_to(ROOT)}: missing")
            generated_skill_names: list[str] = []
        elif not generated_skills_dir.is_dir():
            errors.append(
                f"{generated_skills_dir.relative_to(ROOT)}: must be a directory"
            )
            generated_skill_names = []
        else:
            generated_skill_names = sorted(
                path.name for path in generated_skills_dir.iterdir() if path.is_dir()
            )
            if generated_skill_names != sorted(package_skills):
                errors.append(
                    f"{generated_skills_dir.relative_to(ROOT)}/: generated skills must match package config"
                )

        for skill in package_skills:
            canonical_dir = SKILLS_DIR / skill
            generated_dir = generated_skills_dir / skill
            if not generated_dir.exists():
                errors.append(f"{generated_dir.relative_to(ROOT)}: missing")
                continue
            if not generated_dir.is_dir():
                errors.append(f"{generated_dir.relative_to(ROOT)}: must be a directory")
                continue
            validate_agent_skill_spec(generated_dir, errors)
            canonical_files = {
                path.relative_to(canonical_dir)
                for path in canonical_dir.rglob("*")
                if path.is_file()
            }
            generated_files = {
                path.relative_to(generated_dir)
                for path in generated_dir.rglob("*")
                if path.is_file()
            }
            for missing in sorted(str(path) for path in canonical_files - generated_files):
                errors.append(f"{generated_dir.relative_to(ROOT)}/{missing}: missing from bundle")
            for extra in sorted(str(path) for path in generated_files - canonical_files):
                errors.append(f"{generated_dir.relative_to(ROOT)}/{extra}: not in canonical skill")
            for rel in sorted(canonical_files & generated_files, key=str):
                if (canonical_dir / rel).read_bytes() != (generated_dir / rel).read_bytes():
                    errors.append(f"{generated_dir.relative_to(ROOT)}/{rel}: must match canonical file")
                canonical_mode = (canonical_dir / rel).stat().st_mode & 0o111
                generated_mode = (generated_dir / rel).stat().st_mode & 0o111
                if canonical_mode != generated_mode:
                    errors.append(
                        f"{generated_dir.relative_to(ROOT)}/{rel}: file mode must match canonical file"
                    )

    for skill, plugin_names in sorted(skill_memberships.items()):
        if len(plugin_names) > 1:
            errors.append(
                f"packaging/: skill {skill} belongs to multiple plugins: {', '.join(plugin_names)}"
            )
    if sorted(skill_memberships) != sorted(canonical_skill_names):
        errors.append("packaging/: combined plugin skills must match canonical skill directories")

    if PLUGINS_DIR.exists():
        generated_plugin_names = sorted(path.name for path in PLUGINS_DIR.iterdir() if path.is_dir())
        if generated_plugin_names != sorted(expected_plugin_names):
            errors.append("plugins/: generated plugin directories must match package configs")

    config_by_name = {str(config.get("name")): config for config in configs}
    publishable_plugin_names = sorted(
        str(config.get("name"))
        for config in configs
        if isinstance(config.get("skills"), list) and config.get("skills")
    )
    marketplace_paths = [
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / ".github" / "plugin" / "marketplace.json",
    ]
    legacy_marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"
    if legacy_marketplace_path.exists():
        errors.append(f"{legacy_marketplace_path.relative_to(ROOT)}: legacy marketplace must not exist")
    for path in marketplace_paths:
        marketplace = load_json(path, errors)
        if not marketplace:
            continue
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            errors.append(f"{path.relative_to(ROOT)}: plugins must be a non-empty array")
            continue
        if path.parts[-3:-1] == (".github", "plugin") and not isinstance(
            marketplace.get("owner"), dict
        ):
            errors.append(f"{path.relative_to(ROOT)}: owner must be an object")

        entries: dict[str, dict[str, object]] = {}
        for entry in plugins:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                errors.append(f"{path.relative_to(ROOT)}: every plugin entry must have a name")
                continue
            name = str(entry["name"])
            if name in entries:
                errors.append(f"{path.relative_to(ROOT)}: duplicate plugin entry: {name}")
            entries[name] = entry
        if sorted(entries) != publishable_plugin_names:
            errors.append(f"{path.relative_to(ROOT)}: plugin entries must match publishable package configs")

        for plugin_name, entry in entries.items():
            if path.parts[-3:-1] == (".agents", "plugins"):
                source = entry.get("source")
                source_path = source.get("path") if isinstance(source, dict) else None
            else:
                source_path = entry.get("source")
            expected_source = f"./plugins/{plugin_name}"
            if source_path != expected_source:
                errors.append(
                    f"{path.relative_to(ROOT)}: {plugin_name} source must point to {expected_source}"
                )
            elif not (ROOT / expected_source[2:]).exists():
                errors.append(f"{path.relative_to(ROOT)}: source path does not exist: {expected_source}")
            config = config_by_name.get(plugin_name)
            if config and "version" in entry and entry.get("version") != config.get("version"):
                errors.append(
                    f"{path.relative_to(ROOT)}: {plugin_name} version must match package config"
                )

        if path.parts[-3:-1] == (".agents", "plugins"):
            interface = marketplace.get("interface")
            expected_display_name = next(
                (
                    config.get("marketplace", {}).get("display_name")
                    for config in configs
                    if isinstance(config.get("marketplace"), dict)
                ),
                None,
            )
            if (
                not isinstance(interface, dict)
                or interface.get("displayName") != expected_display_name
            ):
                errors.append(
                    f"{path.relative_to(ROOT)}: interface.displayName must match marketplace display metadata"
                )


def validate_shared_conventions(
    errors: list[str], configs: list[dict[str, object]] | None = None
) -> None:
    source = ROOT / "_shared" / "conventions.md"
    configs = configs if configs is not None else load_package_configs(errors)
    consumers = [
        consumer
        for config in configs
        for consumer in config.get("shared_conventions_consumers", [])
        if isinstance(consumer, str)
    ]
    configured = set(consumers)
    # Config drift must fail loudly: a vendored copy in a skill that is not
    # listed would be neither synced nor drift-checked. This scan runs even
    # when the config key is missing entirely.
    for skill_dir in skill_dirs():
        vendored = skill_dir / "references" / "conventions.md"
        if vendored.exists() and skill_dir.name not in configured:
            errors.append(
                f"skills/{skill_dir.name}/references/conventions.md: exists but the skill is not listed in shared_conventions_consumers"
            )
    if not consumers:
        return
    if not source.exists():
        errors.append(
            "_shared/conventions.md: missing while shared_conventions_consumers is set in packaging config"
        )
        return
    header = "<!-- GENERATED from _shared/conventions.md - edit there, then run scripts/sync-shared-conventions.py -->\n\n"
    expected = header + source.read_text(encoding="utf-8")
    for name in consumers:
        target = SKILLS_DIR / name / "references" / "conventions.md"
        if not target.exists():
            errors.append(f"skills/{name}/references/conventions.md: missing; run scripts/sync-shared-conventions.py")
        elif target.read_text(encoding="utf-8") != expected:
            errors.append(f"skills/{name}/references/conventions.md: stale; run scripts/sync-shared-conventions.py")


def main() -> int:
    errors: list[str] = []
    for artifact_error in verify_vendored_artifacts():
        errors.append(f"vendor/: {artifact_error}")
    configs = load_package_configs(errors)
    canonical_skill_names = validate_skills(errors)
    validate_cross_skill_references(canonical_skill_names, errors)
    validate_packaging(canonical_skill_names, errors, configs)
    validate_shared_conventions(errors, configs)

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Skill repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
