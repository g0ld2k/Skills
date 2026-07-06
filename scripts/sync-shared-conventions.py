#!/usr/bin/env python3
"""Vendor _shared/conventions.md into consumer skills' references/."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "_shared" / "conventions.md"
CONFIG = ROOT / "packaging" / "g0ld2k-skills.json"
HEADER = "<!-- GENERATED from _shared/conventions.md - edit there, then run scripts/sync-shared-conventions.py -->\n\n"


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    consumers = config.get("shared_conventions_consumers", [])
    body = HEADER + SOURCE.read_text(encoding="utf-8")
    for name in consumers:
        target = ROOT / "skills" / name / "references" / "conventions.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        print(f"synced: {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
