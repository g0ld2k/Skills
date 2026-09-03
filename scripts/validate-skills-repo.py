#!/usr/bin/env python3
"""Validate the repository's Agent Plugins v1 manifest and skill publishing shape."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from shared_conventions import HEADER, consumer_names


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
LEGACY_SKILLS_DIR = ROOT / "Skills"
PLUGIN_MANIFEST = ROOT / "plugin.json"
PLUGIN_SCHEMA = ROOT / "schemas" / "agent-plugins" / "1.0.0" / "plugin.schema.json"
EXPLICIT_ONLY_SKILLS = {
    "integration-branch-orchestrator",
    "work-request-orchestration",
}
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BLOCK_SCALAR_HEADER_RE = re.compile(r"^[|>](?:[+-][1-9]?|[1-9][+-]?)?$")
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


DOUBLE_QUOTED_ESCAPES = {
    "0": "\0",
    "a": "\a",
    "b": "\b",
    "t": "\t",
    "n": "\n",
    "v": "\v",
    "f": "\f",
    "r": "\r",
    "e": "\x1b",
    " ": " ",
    '"': '"',
    "/": "/",
    "\\": "\\",
    "N": "\x85",
    "_": "\xa0",
    "L": "\u2028",
    "P": "\u2029",
}
HEX_ESCAPE_WIDTHS = {"x": 2, "u": 4, "U": 8}


def decode_quoted_scalar(value: str) -> str:
    """Decode the YAML single- or double-quoted scalar forms used here."""
    if not value or value[0] not in {"'", '"'}:
        return value
    quote = value[0]
    if len(value) < 2 or value[-1] != quote:
        raise ValueError("unterminated quoted scalar")

    inner = value[1:-1]
    if quote == "'":
        result: list[str] = []
        index = 0
        while index < len(inner):
            if inner[index] != "'":
                result.append(inner[index])
                index += 1
                continue
            if index + 1 == len(inner) or inner[index + 1] != "'":
                raise ValueError("unescaped apostrophe in single-quoted scalar")
            result.append("'")
            index += 2
        return "".join(result)

    result: list[str] = []
    index = 0
    while index < len(inner):
        character = inner[index]
        if character != "\\":
            if character == '"':
                raise ValueError("unescaped quote in double-quoted scalar")
            result.append(character)
            index += 1
            continue

        index += 1
        if index == len(inner):
            raise ValueError("trailing backslash in double-quoted scalar")
        escape = inner[index]
        if escape in DOUBLE_QUOTED_ESCAPES:
            result.append(DOUBLE_QUOTED_ESCAPES[escape])
            index += 1
            continue
        width = HEX_ESCAPE_WIDTHS.get(escape)
        if width is None:
            raise ValueError(f"unsupported double-quoted escape: \\{escape}")
        digits = inner[index + 1 : index + 1 + width]
        if len(digits) != width or not all(char in "0123456789abcdefABCDEF" for char in digits):
            raise ValueError(f"invalid double-quoted escape: \\{escape}{digits}")
        codepoint = int(digits, 16)
        if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
            raise ValueError(f"invalid Unicode scalar: U+{codepoint:04X}")
        result.append(chr(codepoint))
        index += width + 1
    return "".join(result)


YAML_INTEGER_RE = re.compile(
    r"[-+]?(?:[0-9][0-9_]*|0o[0-7_]+|0x[0-9a-fA-F_]+)$"
)
YAML_FLOAT_RE = re.compile(
    r"[-+]?(?:(?:[0-9][0-9_]*)?\.[0-9_]+(?:[eE][-+]?[0-9]+)?|"
    r"[0-9][0-9_]*[eE][-+]?[0-9]+|\.inf|\.Inf|\.INF|\.nan|\.NaN|\.NAN)$"
)


def decode_yaml_scalar(value: str) -> object:
    """Decode the supported YAML scalar node without string-coercing types."""
    if not value:
        return ""
    if value[0] in {"'", '"'}:
        return decode_quoted_scalar(value)
    if value[0] in {"&", "*", "!"}:
        raise ValueError("anchors, aliases, and explicit tags are not supported")
    if value[0] in {"[", "{"}:
        raise ValueError("flow collections are not supported")

    lowered = value.lower()
    if lowered in {"null", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if YAML_INTEGER_RE.fullmatch(value):
        digits = value.replace("_", "")
        unsigned = digits.lstrip("-+")
        base = 8 if unsigned.startswith("0o") else 16 if unsigned.startswith("0x") else 10
        return int(digits, base)
    if YAML_FLOAT_RE.fullmatch(value):
        return float(value.replace("_", ""))
    return value


def strip_yaml_inline_comment(value: str) -> str:
    """Remove a YAML comment while preserving hashes inside quoted scalars."""
    quote: str | None = None
    index = 0
    while index < len(value):
        character = value[index]
        if quote == "'":
            if character == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    index += 2
                    continue
                quote = None
        elif quote == '"':
            if character == "\\":
                index += 2
                continue
            if character == '"':
                quote = None
        elif character in {"'", '"'}:
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        index += 1
    return value


def decode_block_scalar(header: str, source_lines: list[str]) -> str:
    """Decode the folding and chomping needed by top-level frontmatter."""
    nonempty = [line for line in source_lines if line.strip()]
    indicated_indent = next((int(char) for char in header if char.isdigit()), None)
    indent = indicated_indent or min(
        (len(line) - len(line.lstrip(" ")) for line in nonempty), default=0
    )
    lines = [line[indent:] if line.strip() else "" for line in source_lines]
    more_indented = [
        bool(line.strip()) and len(line) - len(line.lstrip(" ")) > indent
        for line in source_lines
    ]
    if header.startswith("|"):
        value = "\n".join(lines)
    else:
        folded = [lines[0]] if lines else []
        for index in range(1, len(lines)):
            previous = lines[index - 1]
            current = lines[index]
            if previous and not current:
                separator = ""
            elif not previous or more_indented[index - 1] or more_indented[index]:
                separator = "\n"
            else:
                separator = " "
            folded.extend((separator, current))
        value = "".join(folded)

    value = value.rstrip("\n")
    if "-" in header:
        return value
    if "+" in header:
        trailing_blanks = 0
        for line in reversed(lines):
            if line:
                break
            trailing_blanks += 1
        return value + "\n" * max(1, trailing_blanks + 1)
    return value + "\n"


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
        raw_value = strip_yaml_inline_comment(value.strip())
        is_quoted = bool(raw_value) and raw_value[0] in {"'", '"'}
        block_header = (
            raw_value
            if not is_quoted and BLOCK_SCALAR_HEADER_RE.fullmatch(raw_value)
            else None
        )
        if raw_value and raw_value[0] not in {"'", '"'} and ": " in raw_value:
            return {}, f"invalid YAML scalar for {current_key}: quote values containing ': '"
        try:
            parsed_value = decode_yaml_scalar(raw_value)
        except ValueError as exc:
            return {}, f"invalid YAML scalar for {current_key}: {exc}"
        if block_header is not None:
            block_lines: list[str] = []
            while index < len(frontmatter_lines):
                block_line = frontmatter_lines[index]
                if block_line.strip() and not block_line.startswith((" ", "\t")):
                    break
                block_lines.append(block_line)
                index += 1
            data[current_key] = decode_block_scalar(block_header, block_lines)
        elif parsed_value is not None and parsed_value != "":
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


def validate_skill_description(
    name: str,
    description: object,
    skill_file: Path,
    errors: list[str],
) -> None:
    """Apply the invocation-specific description policy."""
    if not isinstance(description, str):
        errors.append(f"{skill_file}: description must be a string")
        return
    if not description:
        return
    if name in EXPLICIT_ONLY_SKILLS:
        if (
            not description.strip()
            or description.splitlines() != [description]
            or description.startswith("Use when")
        ):
            errors.append(
                f"{skill_file}: explicit-only description must be a one-line human-facing summary"
            )
        return
    if not description.startswith("Use when"):
        errors.append(f"{skill_file}: description must start with 'Use when'")


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

        description = frontmatter.get("description", "")
        validate_skill_description(
            name,
            description,
            Path("skills") / name / "SKILL.md",
            errors,
        )

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

        # Explicit-only invocation needs a guard per client: Claude Code reads
        # disable-model-invocation from frontmatter, Codex reads
        # policy.allow_implicit_invocation from agents/openai.yaml (checked
        # below). Both are required so neither install path can invoke a
        # state-changing orchestrator implicitly.
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



def validate_shared_conventions(errors: list[str]) -> None:
    source = ROOT / "_shared" / "conventions.md"
    consumers = consumer_names(SKILLS_DIR)
    if not consumers:
        return
    if not source.exists():
        errors.append(
            "_shared/conventions.md: missing while skills reference references/conventions.md"
        )
        return
    expected = HEADER + source.read_text(encoding="utf-8")
    for name in consumers:
        target = SKILLS_DIR / name / "references" / "conventions.md"
        if not target.exists():
            errors.append(f"skills/{name}/references/conventions.md: missing; run scripts/sync-shared-conventions.py")
        elif target.read_text(encoding="utf-8") != expected:
            errors.append(f"skills/{name}/references/conventions.md: stale; run scripts/sync-shared-conventions.py")
    # Drift must fail loudly: a vendored copy in a skill whose instructions do
    # not reference it would be neither synced nor drift-checked.
    for skill_dir in skill_dirs():
        vendored = skill_dir / "references" / "conventions.md"
        if vendored.exists() and skill_dir.name not in set(consumers):
            errors.append(
                f"skills/{skill_dir.name}/references/conventions.md: exists but SKILL.md does not reference it"
            )


def check_against_schema(value: object, schema: dict, path: str, errors: list[str]) -> None:
    """Validate `value` against the subset of JSON Schema the pinned manifest uses."""
    expected = schema.get("type")
    types = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
    }
    if expected in types and not isinstance(value, types[expected]):
        errors.append(f"{path}: must be of type {expected}")
        return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}")
    if isinstance(value, str):
        if "pattern" in schema and not re.match(schema["pattern"], value):
            errors.append(f"{path}: does not match the required pattern")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: must be at least {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: must be at most {schema['maxLength']} characters")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            check_against_schema(item, schema["items"], f"{path}[{index}]", errors)
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field '{key}'")
        if schema.get("additionalProperties") is False:
            for key in sorted(set(value) - set(properties)):
                errors.append(f"{path}: unsupported field '{key}'")
        extra = schema.get("additionalProperties")
        for key, item in value.items():
            if key in properties:
                check_against_schema(item, properties[key], f"{path}.{key}", errors)
            elif isinstance(extra, dict):
                check_against_schema(item, extra, f"{path}.{key}", errors)


def validate_plugin_manifest(errors: list[str]) -> None:
    """Check plugin.json against the pinned Agent Plugins v1 manifest schema."""
    schema = load_json(PLUGIN_SCHEMA, errors)
    manifest = load_json(PLUGIN_MANIFEST, errors)
    if schema is None or manifest is None:
        return
    check_against_schema(manifest, schema, "plugin.json", errors)
    validate_marketplace_adapters(manifest, errors)


def validate_marketplace_adapters(manifest: dict, errors: list[str]) -> None:
    """Keep each client adapter's plugin entry in step with the root manifest.

    The generated packaging layer used to guarantee this by construction. The
    adapters are now hand-maintained, so a drifted name/description/version
    would otherwise ship silently.
    """
    name = manifest.get("name")
    # Each adapter declares a different entry shape, so the mirrored fields are
    # per-adapter. A field listed here is required: treating its absence as
    # "synchronized" would let a deletion pass while a replacement is caught.
    adapters = {
        ".agents/plugins/marketplace.json": (
            lambda entry: entry.get("source", {}).get("path"),
            (),
        ),
        ".github/plugin/marketplace.json": (
            lambda entry: entry.get("source"),
            ("version", "description"),
        ),
    }
    for rel, (source_of, mirrored_fields) in adapters.items():
        adapter = load_json(ROOT / rel, errors)
        if adapter is None:
            continue
        entries = adapter.get("plugins", [])
        if [entry.get("name") for entry in entries] != [name]:
            errors.append(f"{rel}: plugins must list exactly the root manifest's '{name}'")
            continue
        entry = entries[0]
        if source_of(entry) != ".":
            errors.append(f"{rel}: {name} source must point at the repository root '.'")
        for field in mirrored_fields:
            if field not in entry:
                errors.append(f"{rel}: {name} must declare {field} to match plugin.json")
            elif entry[field] != manifest.get(field):
                errors.append(f"{rel}: {name} {field} must match plugin.json")

def main() -> int:
    errors: list[str] = []
    validate_plugin_manifest(errors)
    canonical_skill_names = validate_skills(errors)
    validate_cross_skill_references(canonical_skill_names, errors)
    validate_shared_conventions(errors)

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Skill repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
