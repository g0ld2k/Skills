#!/usr/bin/env python3
"""Validate the repository's skill publishing and plugin packaging shape."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
LEGACY_SKILLS_DIR = ROOT / "Skills"
PLUGIN_NAME = "g0ld2k-skills"
PLUGIN_DIR = ROOT / "plugins" / PLUGIN_NAME
PACKAGE_CONFIG = ROOT / "packaging" / f"{PLUGIN_NAME}.json"
EXPLICIT_ONLY_SKILLS = {
    "integration-branch-orchestrator",
    "pr-closeout-loop",
    "simplify",
    "work-request-orchestration",
}
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RETIRED_SKILL_NAMES = {"codex-pr-approval-loop"}
EXTERNAL_SKILL_PREFIXES = ("superpowers:",)
# Single-word command tokens that legitimately follow Use/run/invoke in prose.
# Extend only with commands/tools, never with skill names.
NON_SKILL_TOKENS = {"gh", "git", "jq", "rg", "make", "mktemp", "shellcheck"}
# Matches: Use `name`, use `name`, invoke `name`, delegating to `name`, run `name`
SKILL_REF_CONTEXT_RE = re.compile(
    r"(?:[Uu]se|invoke|delegat\w+ to|[Rr]un)\s+`([a-z0-9][a-z0-9:-]*[a-z0-9])`"
)
# Companion-list bullets like: - `pr-comment-review` for triaging...
COMPANION_REF_RE = re.compile(
    r"^\s*-\s+`([a-z0-9][a-z0-9:-]*[a-z0-9])`\s+(?:for|to|when|before|after)\b",
    re.MULTILINE,
)


def has_exact_child(parent: Path, name: str) -> bool:
    if not parent.exists():
        return False
    return any(child.name == name for child in parent.iterdir())


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> tuple[dict[str, object], str | None]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing YAML frontmatter"

    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return {}, "unterminated YAML frontmatter"

    data: dict[str, object] = {}
    current_key: str | None = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            if current_key and line.strip().startswith("- "):
                existing = data.setdefault(current_key, [])
                if isinstance(existing, list):
                    existing.append(strip_quotes(line.strip()[2:]))
            continue

        key, separator, value = line.partition(":")
        if not separator:
            continue
        current_key = key.strip()
        parsed_value = strip_quotes(value.strip())
        if parsed_value == "true":
            data[current_key] = True
        elif parsed_value == "false":
            data[current_key] = False
        elif parsed_value:
            data[current_key] = parsed_value
        else:
            data[current_key] = []

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
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"skills/{name}/SKILL.md: missing")
            continue

        frontmatter, parse_error = parse_frontmatter(skill_file)
        if parse_error:
            errors.append(f"skills/{name}/SKILL.md: {parse_error}")
            continue

        for key in ("name", "description", "license"):
            if key not in frontmatter or not frontmatter[key]:
                errors.append(f"skills/{name}/SKILL.md: missing frontmatter key: {key}")

        description = str(frontmatter.get("description", ""))
        if description and not description.startswith("Use when"):
            errors.append(f"skills/{name}/SKILL.md: description must start with 'Use when'")

        declared_name = frontmatter.get("name")
        if declared_name != name:
            errors.append(f"skills/{name}/SKILL.md: name must match directory")
        if not SKILL_NAME_RE.match(name):
            errors.append(f"skills/{name}/: directory name must be kebab-case")
        if frontmatter.get("license") != "MIT":
            errors.append(f"skills/{name}/SKILL.md: license must be MIT")
        if "tools" in frontmatter:
            errors.append(f"skills/{name}/SKILL.md: tools frontmatter is not allowed")
        if "allowed-tools" in frontmatter:
            errors.append(f"skills/{name}/SKILL.md: allowed-tools has no approved exception")
        if "user-invocable" in frontmatter:
            errors.append(f"skills/{name}/SKILL.md: user-invocable must be absent")

        has_disable = frontmatter.get("disable-model-invocation") is True
        if name in EXPLICIT_ONLY_SKILLS and not has_disable:
            errors.append(f"skills/{name}/SKILL.md: disable-model-invocation must be true")
        if name not in EXPLICIT_ONLY_SKILLS and "disable-model-invocation" in frontmatter:
            errors.append(f"skills/{name}/SKILL.md: disable-model-invocation must be absent")

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
        SKILLS_DIR.glob("*/references/*.md")
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


def validate_packaging(canonical_skill_names: list[str], errors: list[str]) -> None:
    config = load_json(PACKAGE_CONFIG, errors)
    if not config:
        return

    package_skills = config.get("skills")
    if not isinstance(package_skills, list) or not all(isinstance(item, str) for item in package_skills):
        errors.append(f"{PACKAGE_CONFIG.relative_to(ROOT)}: skills must be a string array")
        return

    if sorted(package_skills) != sorted(canonical_skill_names):
        errors.append(f"{PACKAGE_CONFIG.relative_to(ROOT)}: skills must match canonical skill directories")

    for skill in package_skills:
        if not (SKILLS_DIR / skill).exists():
            errors.append(f"{PACKAGE_CONFIG.relative_to(ROOT)}: listed skill missing from skills/: {skill}")

    version = config.get("version")
    manifest_paths = [
        ROOT / "plugins" / PLUGIN_NAME / "plugin.json",
        ROOT / "plugins" / PLUGIN_NAME / ".claude-plugin" / "plugin.json",
        ROOT / "plugins" / PLUGIN_NAME / ".codex-plugin" / "plugin.json",
    ]
    for path in manifest_paths:
        manifest = load_json(path, errors)
        if not manifest:
            continue
        if manifest.get("name") != PLUGIN_NAME:
            errors.append(f"{path.relative_to(ROOT)}: name must be {PLUGIN_NAME}")
        if manifest.get("version") != version:
            errors.append(f"{path.relative_to(ROOT)}: version must match package config")

    generated_skills_dir = PLUGIN_DIR / "skills"
    if not generated_skills_dir.exists():
        errors.append(f"{generated_skills_dir.relative_to(ROOT)}: missing")
        generated_skill_names: list[str] = []
    else:
        generated_skill_names = sorted(path.name for path in generated_skills_dir.iterdir() if path.is_dir())
        if generated_skill_names != sorted(package_skills):
            errors.append("plugins/g0ld2k-skills/skills/: generated skills must match package config")

    for skill in package_skills:
        canonical_dir = SKILLS_DIR / skill
        generated_dir = generated_skills_dir / skill
        if not generated_dir.exists():
            errors.append(f"{generated_dir.relative_to(ROOT)}: missing")
            continue
        canonical_files = {
            p.relative_to(canonical_dir) for p in canonical_dir.rglob("*") if p.is_file()
        }
        generated_files = {
            p.relative_to(generated_dir) for p in generated_dir.rglob("*") if p.is_file()
        }
        for missing in sorted(str(p) for p in canonical_files - generated_files):
            errors.append(f"{generated_dir.relative_to(ROOT)}/{missing}: missing from bundle")
        for extra in sorted(str(p) for p in generated_files - canonical_files):
            errors.append(f"{generated_dir.relative_to(ROOT)}/{extra}: not in canonical skill")
        for rel in sorted(canonical_files & generated_files, key=str):
            if (canonical_dir / rel).read_bytes() != (generated_dir / rel).read_bytes():
                errors.append(f"{generated_dir.relative_to(ROOT)}/{rel}: must match canonical file")

    marketplace_paths = [
        ROOT / ".claude-plugin" / "marketplace.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / ".github" / "plugin" / "marketplace.json",
    ]
    for path in marketplace_paths:
        marketplace = load_json(path, errors)
        if not marketplace:
            continue
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            errors.append(f"{path.relative_to(ROOT)}: plugins must be a non-empty array")
            continue
        if path.parts[-3:-1] == (".github", "plugin") and not isinstance(marketplace.get("owner"), dict):
            errors.append(f"{path.relative_to(ROOT)}: owner must be an object")
        first = plugins[0]
        if not isinstance(first, dict):
            errors.append(f"{path.relative_to(ROOT)}: first plugin entry must be an object")
            continue
        if first.get("name") != PLUGIN_NAME:
            errors.append(f"{path.relative_to(ROOT)}: plugin name must be {PLUGIN_NAME}")
        if path.parts[-3:-1] == (".agents", "plugins"):
            source = first.get("source")
            source_path = source.get("path") if isinstance(source, dict) else None
        else:
            source_path = first.get("source")
        if source_path != "./plugins/g0ld2k-skills":
            errors.append(f"{path.relative_to(ROOT)}: source must point to ./plugins/g0ld2k-skills")
        elif not (ROOT / source_path[2:]).exists():
            errors.append(f"{path.relative_to(ROOT)}: source path does not exist")


def main() -> int:
    errors: list[str] = []
    canonical_skill_names = validate_skills(errors)
    validate_cross_skill_references(canonical_skill_names, errors)
    validate_packaging(canonical_skill_names, errors)

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Skill repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
