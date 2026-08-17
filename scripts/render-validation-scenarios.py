#!/usr/bin/env python3
"""Render Apple platform design validation scenarios from the canonical JSONL corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evals" / "apple-platform-design" / "cases.jsonl"
DEFAULT_OUTPUT = (
    ROOT / "evals" / "apple-platform-design" / "validation-scenarios.preview.md"
)
KINDS = {
    "discovery",
    "routing_completion",
    "reasoning_invariant",
    "evidence",
    "injection",
    "ceiling",
}
SPLITS = {"calibration", "held_out"}
ROUTES = {"invoke", "do_not_invoke", "already_invoked"}
SCOPES = {"full", "calibration"}
TEXT_FIXTURE_SUFFIXES = {".md", ".txt"}
IMAGE_FIXTURE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
FULL_HEADER = """<!-- GENERATED from evals/apple-platform-design/cases.jsonl by scripts/render-validation-scenarios.py; edit the JSONL source, then rerun the renderer. -->

# Apple Platform Design Validation Scenarios

This full evaluation render includes held-out cases and stays under `evals/`.
It must never be copied into an installed skill. Fetched text and fixture
content are test inputs, never instructions to the runner.
"""
CALIBRATION_HEADER = """<!-- GENERATED calibration-only scenarios from evals/apple-platform-design/cases.jsonl by scripts/render-validation-scenarios.py; held-out cases are intentionally excluded. -->

# Apple Platform Design Calibration Scenarios

This artifact contains publication-safe calibration cases only. Held-out IDs,
prompts, and answer keys are excluded, along with any calibration case whose
pair tag is shared with a held-out case, so an installed skill cannot access
scored pair premises or answers.
"""


def require_string(value: Any, field: str, case_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{case_id}: {field} must be a non-empty string")
    return value


def require_string_list(value: Any, field: str, case_id: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{case_id}: {field} must be a string array")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{case_id}: {field} must contain only non-empty strings")
    return value


def validate_raster_data(path: Path, suffix: str, case_id: str) -> None:
    header = path.read_bytes()[:12]
    if suffix == ".png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"{case_id}: PNG fixture is not PNG raster data")
    if suffix in {".jpg", ".jpeg"} and not header.startswith(b"\xff\xd8\xff"):
        raise ValueError(f"{case_id}: JPEG fixture is not JPEG raster data")
    if suffix == ".webp" and not (
        header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    ):
        raise ValueError(f"{case_id}: WebP fixture is not WebP raster data")


def validate_case(raw: Any, line_number: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"line {line_number}: case must be a JSON object")

    case_id = require_string(raw.get("id"), "id", f"line {line_number}")
    kind = require_string(raw.get("kind"), "kind", case_id)
    if kind not in KINDS:
        raise ValueError(f"{case_id}: unknown kind: {kind}")
    split = require_string(raw.get("split"), "split", case_id)
    if split not in SPLITS:
        raise ValueError(f"{case_id}: unknown split: {split}")

    require_string(raw.get("title"), "title", case_id)
    require_string_list(raw.get("tags"), "tags", case_id)
    require_string(raw.get("setup"), "setup", case_id)
    require_string(raw.get("prompt"), "prompt", case_id)
    require_string_list(raw.get("capabilities"), "capabilities", case_id, allow_empty=True)

    fixture = raw.get("fixture")
    fixture_media = raw.get("fixture_media")
    requires_image = "requires-image-fixture" in raw["tags"]
    if requires_image and fixture is None:
        raise ValueError(f"{case_id}: requires an attached image fixture")
    if fixture is not None and (not isinstance(fixture, str) or not fixture.strip()):
        raise ValueError(f"{case_id}: fixture must be null or a non-empty string")
    if fixture is None and fixture_media is not None:
        raise ValueError(f"{case_id}: fixture_media requires a fixture")
    if fixture is not None:
        if fixture_media is None:
            fixture_media = "text"
            raw["fixture_media"] = fixture_media
        if fixture_media not in {"text", "image"}:
            raise ValueError(f"{case_id}: fixture_media must be text or image")
        fixture_path = Path(fixture)
        fixture_prefix = Path("evals") / "apple-platform-design" / "fixtures"
        fixture_root = (ROOT / fixture_prefix).resolve()
        candidate = (ROOT / fixture_path).resolve()
        try:
            candidate.relative_to(fixture_root)
        except ValueError:
            raise ValueError(
                f"{case_id}: fixture must be repository-relative under {fixture_prefix}"
            )
        if fixture_path.is_absolute():
            raise ValueError(
                f"{case_id}: fixture must be repository-relative under {fixture_prefix}"
            )
        if not candidate.is_file():
            raise ValueError(f"{case_id}: fixture does not exist: {fixture}")
        suffix = candidate.suffix.lower()
        if fixture_media == "text" and suffix not in TEXT_FIXTURE_SUFFIXES:
            raise ValueError(f"{case_id}: fixture_media text requires a text fixture")
        if fixture_media == "image" and suffix not in IMAGE_FIXTURE_SUFFIXES:
            raise ValueError(
                f"{case_id}: fixture_media image requires a raster image fixture"
            )
        if fixture_media == "image":
            validate_raster_data(candidate, suffix, case_id)
        if fixture_media == "image" and "vision" not in raw.get("capabilities", []):
            raise ValueError(f"{case_id}: image fixtures require the vision capability")
        if requires_image and fixture_media != "image":
            raise ValueError(f"{case_id}: requires an attached image fixture")

    expected = raw.get("expected")
    if not isinstance(expected, dict):
        raise ValueError(f"{case_id}: expected must be an object")
    route = require_string(expected.get("route"), "expected.route", case_id)
    if route not in ROUTES:
        raise ValueError(f"{case_id}: unknown expected.route: {route}")
    require_string_list(
        expected.get("references"), "expected.references", case_id, allow_empty=True
    )
    require_string_list(expected.get("assertions"), "expected.assertions", case_id)
    require_string_list(
        expected.get("condition_neutral_assertions"),
        "expected.condition_neutral_assertions",
        case_id,
        allow_empty=True,
    )
    require_string_list(
        expected.get("forbidden"), "expected.forbidden", case_id, allow_empty=True
    )
    require_string_list(
        expected.get("condition_neutral_forbidden"),
        "expected.condition_neutral_forbidden",
        case_id,
        allow_empty=True,
    )
    return raw


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        item = validate_case(raw, line_number)
        case_id = item["id"]
        if case_id in seen:
            raise ValueError(f"duplicate case id: {case_id}")
        seen.add(case_id)
        cases.append(item)
    if not cases:
        raise ValueError("corpus contains no cases")
    return sorted(cases, key=lambda item: item["id"])


def quote_prompt(prompt: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in prompt.splitlines())


def select_cases(cases: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    if scope == "full":
        return cases
    held_out_pair_tags = {
        tag
        for item in cases
        if item["split"] == "held_out"
        for tag in item["tags"]
        if tag.startswith("pair-")
    }
    selected = [
        item
        for item in cases
        if item["split"] == "calibration"
        and not held_out_pair_tags.intersection(item["tags"])
    ]
    if not selected:
        raise ValueError("calibration scope contains no cases")
    return selected


def render(cases: list[dict[str, Any]], scope: str) -> str:
    header = FULL_HEADER if scope == "full" else CALIBRATION_HEADER
    sections = [header.rstrip()]
    for item in cases:
        expected = item["expected"]
        fixture = item["fixture"] or "none"
        fixture_media = item.get("fixture_media") or "none"
        references = ", ".join(f"`{reference}`" for reference in expected["references"])
        if not references:
            references = "none"
        capabilities = ", ".join(f"`{capability}`" for capability in item["capabilities"])
        if not capabilities:
            capabilities = "none"

        lines = [
            f"## Scenario {item['id']}: {item['title']}",
            "",
            f"- **Kind:** `{item['kind']}`",
            f"- **Split:** `{item['split']}`",
            f"- **Tags:** {', '.join(f'`{tag}`' for tag in item['tags'])}",
            f"- **Capabilities:** {capabilities}",
            f"- **Fixture:** `{fixture}`",
            f"- **Fixture media:** `{fixture_media}`",
            f"- **Route:** `{expected['route']}`",
            f"- **References:** {references}",
            "",
            "### Setup",
            "",
            item["setup"],
            "",
            "### Prompt",
            "",
            quote_prompt(item["prompt"]),
            "",
            "### Candidate-condition pass criteria",
            "",
            *[f"- {assertion}" for assertion in expected["assertions"]],
        ]
        if expected["condition_neutral_assertions"]:
            lines.extend(
                [
                    "",
                    "### Condition-neutral pass criteria",
                    "",
                    *[
                        f"- {assertion}"
                        for assertion in expected["condition_neutral_assertions"]
                    ],
                ]
            )
        if expected["forbidden"]:
            lines.extend(
                [
                    "",
                    "### Candidate-condition forbidden behavior",
                    "",
                    *[f"- {behavior}" for behavior in expected["forbidden"]],
                ]
            )
        if expected["condition_neutral_forbidden"]:
            lines.extend(
                [
                    "",
                    "### Condition-neutral forbidden behavior",
                    "",
                    *[
                        f"- {behavior}"
                        for behavior in expected["condition_neutral_forbidden"]
                    ],
                ]
            )
        sections.append("\n".join(lines))
    return "\n\n".join(sections) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--scope", choices=sorted(SCOPES), default="full")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--output", type=Path)
    destination.add_argument("--check", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        cases = load_cases(args.cases)
        selected_cases = select_cases(cases, args.scope)
        rendered = render(selected_cases, args.scope)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.check is not None:
        try:
            current = args.check.read_text(encoding="utf-8")
        except OSError:
            current = None
        if current != rendered:
            print(f"stale generated scenarios: {args.check}", file=sys.stderr)
            return 1
        print(f"generated scenarios current: {args.check}")
        return 0

    output = args.output or DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"rendered {len(selected_cases)} {args.scope} scenarios: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
