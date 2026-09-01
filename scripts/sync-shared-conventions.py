#!/usr/bin/env python3
"""Vendor _shared/conventions.md into consumer skills' references/."""
from pathlib import Path

from shared_conventions import HEADER, consumer_names

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "_shared" / "conventions.md"
SKILLS_DIR = ROOT / "skills"


def main() -> int:
    body = HEADER + SOURCE.read_text(encoding="utf-8")
    for name in consumer_names(SKILLS_DIR):
        target = ROOT / "skills" / name / "references" / "conventions.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        print(f"synced: {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
