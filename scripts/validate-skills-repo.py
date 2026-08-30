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
PACKAGING_DIR = ROOT / "packaging"
PLUGINS_DIR = ROOT / "plugins"
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
# Single-word command tokens that legitimately follow Use/run/invoke in prose.
# Extend only with commands/tools, never with skill names.
NON_SKILL_TOKENS = {"gh", "git", "jq", "rg", "make", "mktemp", "shellcheck"}
# Matches: Use `name`, use `name`, Invoke `name`, delegating to `name`, Run `name`
SKILL_REF_CONTEXT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:[Uu]se|[Ii]nvoke|[Dd]elegat\w+ to|[Rr]un)\s+`([a-z0-9][a-z0-9:-]*[a-z0-9])`"
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
    frontmatter_lines = lines[1:end]
    index = 0
    while index < len(frontmatter_lines):
        line = frontmatter_lines[index]
        index += 1
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
        elif parsed_value in {">", ">-", ">+", "|", "|-", "|+"}:
            block_lines: list[str] = []
            while index < len(frontmatter_lines):
                block_line = frontmatter_lines[index]
                if block_line.strip() and not block_line.startswith((" ", "\t")):
                    break
                if block_line.strip():
                    block_lines.append(block_line.strip())
                index += 1
            data[current_key] = (
                " ".join(block_lines) if parsed_value == ">" else "\n".join(block_lines)
            )
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


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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

        if "disable-model-invocation" in frontmatter:
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
