#!/usr/bin/env python3
"""Vendor shared reference material from _shared/ into consumer skills.

Two mechanisms, both driven by packaging/g0ld2k-skills.json:

- ``shared_conventions_consumers``: legacy single-file sync of
  _shared/conventions.md into skills/<name>/references/conventions.md.
- ``shared_reference_groups``: named groups, each with a ``source``
  directory under _shared/ and a ``consumers`` list. Every file in the
  source directory is vendored into skills/<name>/references/<group>/,
  replacing that directory wholesale so deletions propagate too.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "packaging" / "g0ld2k-skills.json"


def generated_header(source_rel: str) -> str:
    return (
        f"<!-- GENERATED from {source_rel} - edit there, then run "
        "scripts/sync-shared-conventions.py -->\n\n"
    )


def sync_conventions(config: dict) -> None:
    source = ROOT / "_shared" / "conventions.md"
    consumers = config.get("shared_conventions_consumers", [])
    if not consumers:
        return
    body = generated_header("_shared/conventions.md") + source.read_text(encoding="utf-8")
    for name in consumers:
        target = ROOT / "skills" / name / "references" / "conventions.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        print(f"synced: {target.relative_to(ROOT)}")


def sync_groups(config: dict) -> None:
    groups = config.get("shared_reference_groups", {})
    for group_name, group in groups.items():
        source_dir = ROOT / group["source"]
        files = sorted(p for p in source_dir.rglob("*") if p.is_file())
        if not files:
            raise SystemExit(f"shared group '{group_name}': no files under {group['source']}")
        for consumer in group.get("consumers", []):
            target_dir = ROOT / "skills" / consumer / "references" / group_name
            if target_dir.exists():
                shutil.rmtree(target_dir)
            for source_file in files:
                rel = source_file.relative_to(source_dir)
                target = target_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                source_rel = source_file.relative_to(ROOT).as_posix()
                body = generated_header(source_rel) + source_file.read_text(encoding="utf-8")
                target.write_text(body, encoding="utf-8")
                print(f"synced: {target.relative_to(ROOT)}")


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    sync_conventions(config)
    sync_groups(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
