"""Shared-conventions discovery used by repository tooling."""

from pathlib import Path


REFERENCE_PATH = "references/conventions.md"
HEADER = "<!-- GENERATED from _shared/conventions.md - edit there, then run scripts/sync-shared-conventions.py -->\n\n"


def consumer_names(skills_dir: Path) -> list[str]:
    """Return skills whose instructions reference the shared conventions copy."""
    if not skills_dir.is_dir():
        return []
    return [
        skill_dir.name
        for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir())
        if (skill_dir / "SKILL.md").is_file()
        and REFERENCE_PATH in (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    ]
