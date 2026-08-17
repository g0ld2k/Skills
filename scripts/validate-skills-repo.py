#!/usr/bin/env python3
"""Validate the repository's skill publishing and plugin packaging shape."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
LEGACY_SKILLS_DIR = ROOT / "Skills"
PACKAGING_DIR = ROOT / "packaging"
PLUGINS_DIR = ROOT / "plugins"
APPLE_DESIGN_CASES = ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
APPLE_DESIGN_CONDITIONS = (
    ROOT / "evals" / "apple-platform-design" / "conditions.json"
)
APPLE_DESIGN_RENDERER = ROOT / "scripts" / "render-validation-scenarios.py"
APPLE_DESIGN_PREVIEW = (
    ROOT
    / "evals"
    / "apple-platform-design"
    / "validation-scenarios.preview.md"
)
APPLE_DESIGN_SCENARIOS = (
    SKILLS_DIR
    / "apple-platform-design"
    / "references"
    / "validation-scenarios.md"
)
APPLE_DESIGN_KINDS = [
    "discovery",
    "routing_completion",
    "reasoning_invariant",
    "evidence",
    "injection",
    "ceiling",
]
APPLE_DESIGN_BASELINE_KINDS = ["discovery", "routing_completion"]
APPLE_DESIGN_CANDIDATE_ASSERTION_KEYS = [
    "expected.assertions",
    "expected.condition_neutral_assertions",
]
APPLE_DESIGN_CANDIDATE_FORBIDDEN_KEYS = [
    "expected.forbidden",
    "expected.condition_neutral_forbidden",
]
APPLE_DESIGN_NEUTRAL_ASSERTION_KEYS = ["expected.condition_neutral_assertions"]
APPLE_DESIGN_NEUTRAL_FORBIDDEN_KEYS = ["expected.condition_neutral_forbidden"]
APPLE_DESIGN_AGGREGATE_RELEASE_GATES = [
    {
        "id": "bounded-context",
        "case_ids": ["ceiling-01", "ceiling-02"],
        "required_tags": ["4k"],
        "runtime": "claude-code",
        "metric": "total_incremental_tokens",
        "p95_max_tokens": 4000,
        "report": ["p95", "maximum"],
    },
    {
        "id": "open-context",
        "case_ids": ["ceiling-03", "ceiling-04"],
        "required_tags": ["8k"],
        "runtime": "claude-code",
        "metric": "total_incremental_tokens",
        "p95_max_tokens": 8000,
        "report": ["p95", "maximum"],
    },
]
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
        manifest_paths = [
            plugin_dir / "plugin.json",
            plugin_dir / ".claude-plugin" / "plugin.json",
            plugin_dir / ".codex-plugin" / "plugin.json",
        ]
        for path in manifest_paths:
            manifest = load_json(path, errors)
            if not manifest:
                continue
            if manifest.get("name") != plugin_name:
                errors.append(f"{path.relative_to(ROOT)}: name must be {plugin_name}")
            if manifest.get("version") != version:
                errors.append(f"{path.relative_to(ROOT)}: version must match package config")

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
        if sorted(entries) != sorted(expected_plugin_names):
            errors.append(f"{path.relative_to(ROOT)}: plugin entries must match package configs")

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


def validate_apple_platform_design_conditions(errors: list[str]) -> bool:
    """Validate the condition policy consumed by the future evaluation runner."""
    initial_error_count = len(errors)
    policy = load_json(APPLE_DESIGN_CONDITIONS, errors)
    if policy is None:
        return False
    relative = APPLE_DESIGN_CONDITIONS.relative_to(ROOT)
    if not isinstance(policy, dict):
        errors.append(f"{relative}: top level must be an object")
        return False

    expected_top_level = {
        "schema_version",
        "candidate_answer_keys",
        "aggregate_release_gates",
        "conditions",
        "condition_neutral_dimensions",
    }
    actual_top_level = set(policy)
    missing_top_level = expected_top_level - actual_top_level
    extra_top_level = actual_top_level - expected_top_level
    if missing_top_level:
        errors.append(
            f"{relative}: missing fields: {', '.join(sorted(missing_top_level))}"
        )
    if extra_top_level:
        errors.append(
            f"{relative}: extra fields: {', '.join(sorted(extra_top_level))}"
        )
    if policy.get("schema_version") != 1:
        errors.append(f"{relative}: schema_version must be 1")

    expected_answer_keys = ["expected.route", "expected.references"]
    if policy.get("candidate_answer_keys") != expected_answer_keys:
        errors.append(
            f"{relative}: candidate_answer_keys must be exactly "
            f"{', '.join(expected_answer_keys)}"
        )
    if policy.get("aggregate_release_gates") != APPLE_DESIGN_AGGREGATE_RELEASE_GATES:
        errors.append(
            f"{relative}: aggregate_release_gates must be exactly the bounded "
            "and open Claude Code context gates"
        )
    expected_dimensions = ["task_quality", "evidence", "completion"]
    if policy.get("condition_neutral_dimensions") != expected_dimensions:
        errors.append(
            f"{relative}: condition_neutral_dimensions must be exactly "
            f"{', '.join(expected_dimensions)}"
        )

    conditions = policy.get("conditions")
    if not isinstance(conditions, dict):
        errors.append(f"{relative}: conditions must be an object")
        return False
    expected_condition_names = {"candidate", "no_skill", "installed_hig_suite"}
    actual_condition_names = set(conditions)
    missing_conditions = expected_condition_names - actual_condition_names
    extra_conditions = actual_condition_names - expected_condition_names
    if missing_conditions:
        errors.append(
            f"{relative}: missing conditions: {', '.join(sorted(missing_conditions))}"
        )
    if extra_conditions:
        errors.append(
            f"{relative}: extra conditions: {', '.join(sorted(extra_conditions))}"
        )

    common_expected = {
        "condition_neutral_quality_scoring": "gate",
    }
    condition_expected: dict[str, dict[str, object]] = {
        "candidate": {
            "case_kinds": APPLE_DESIGN_KINDS,
            "route_scoring": "gate",
            "reference_scoring": "gate",
            "assertion_keys": APPLE_DESIGN_CANDIDATE_ASSERTION_KEYS,
            "forbidden_keys": APPLE_DESIGN_CANDIDATE_FORBIDDEN_KEYS,
            **common_expected,
        },
        "no_skill": {
            "case_kinds": APPLE_DESIGN_BASELINE_KINDS,
            "candidate_setup_clauses": "omit",
            "route_scoring": "descriptive",
            "reference_scoring": "descriptive",
            "assertion_keys": APPLE_DESIGN_NEUTRAL_ASSERTION_KEYS,
            "forbidden_keys": APPLE_DESIGN_NEUTRAL_FORBIDDEN_KEYS,
            **common_expected,
        },
        "installed_hig_suite": {
            "case_kinds": APPLE_DESIGN_BASELINE_KINDS,
            "candidate_setup_clauses": "omit",
            "route_scoring": "descriptive",
            "reference_scoring": "descriptive",
            "assertion_keys": APPLE_DESIGN_NEUTRAL_ASSERTION_KEYS,
            "forbidden_keys": APPLE_DESIGN_NEUTRAL_FORBIDDEN_KEYS,
            **common_expected,
        },
    }
    for condition_name in sorted(expected_condition_names & actual_condition_names):
        condition = conditions[condition_name]
        if not isinstance(condition, dict):
            errors.append(f"{relative}: {condition_name} must be an object")
            continue
        namespace = condition.get("namespace")
        if not isinstance(namespace, str) or not namespace.strip():
            errors.append(f"{relative}: {condition_name}.namespace must be a string")
        expected_fields = condition_expected[condition_name]
        allowed_fields = {"namespace", *expected_fields}
        missing_fields = allowed_fields - set(condition)
        extra_fields = set(condition) - allowed_fields
        if missing_fields:
            errors.append(
                f"{relative}: {condition_name} missing fields: "
                f"{', '.join(sorted(missing_fields))}"
            )
        if extra_fields:
            errors.append(
                f"{relative}: {condition_name} extra fields: "
                f"{', '.join(sorted(extra_fields))}"
            )
        for field, expected_value in expected_fields.items():
            if condition.get(field) != expected_value:
                rendered_expected = (
                    ", ".join(expected_value)
                    if isinstance(expected_value, list)
                    else str(expected_value)
                )
                errors.append(
                    f"{relative}: {condition_name}.{field} must be {rendered_expected}"
                )

    return len(errors) == initial_error_count


def validate_apple_platform_design_scenarios(errors: list[str]) -> None:
    """Validate the corpus and generated artifacts without leaking held-out cases."""
    if not validate_apple_platform_design_conditions(errors):
        return
    if not APPLE_DESIGN_CASES.exists():
        errors.append("evals/apple-platform-design/cases.jsonl: missing")
        return
    if not APPLE_DESIGN_RENDERER.exists():
        errors.append("scripts/render-validation-scenarios.py: missing")
        return

    def check_target(target: Path, scope: str, command: str) -> bool:
        result = subprocess.run(
            [
                sys.executable,
                str(APPLE_DESIGN_RENDERER),
                "--cases",
                str(APPLE_DESIGN_CASES),
                "--scope",
                scope,
                "--check",
                str(target),
            ],
            capture_output=True,
            text=True,
        )
        relative_target = target.relative_to(ROOT)
        if result.returncode == 0:
            return True
        if result.stderr.startswith("stale generated scenarios:"):
            errors.append(f"{relative_target}: stale; run {command}")
            return False
        detail = result.stderr.strip() or result.stdout.strip() or "unknown renderer failure"
        errors.append(
            f"{relative_target}: could not verify generated scenarios: {detail}"
        )
        return False

    preview_command = "python3 scripts/render-validation-scenarios.py"
    if not check_target(APPLE_DESIGN_PREVIEW, "full", preview_command):
        return

    if not (SKILLS_DIR / "apple-platform-design").exists():
        return

    skill_command = (
        "python3 scripts/render-validation-scenarios.py --scope calibration "
        "--output skills/apple-platform-design/references/validation-scenarios.md"
    )
    check_target(APPLE_DESIGN_SCENARIOS, "calibration", skill_command)


def main() -> int:
    errors: list[str] = []
    configs = load_package_configs(errors)
    canonical_skill_names = validate_skills(errors)
    validate_cross_skill_references(canonical_skill_names, errors)
    validate_packaging(canonical_skill_names, errors, configs)
    validate_shared_conventions(errors, configs)
    validate_apple_platform_design_scenarios(errors)

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Skill repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
