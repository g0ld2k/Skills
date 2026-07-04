#!/usr/bin/env python3
"""Generate product plugin manifests and bundled skill copies."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_CONFIG = ROOT / "packaging" / "g0ld2k-skills.json"
SKILLS_DIR = ROOT / "skills"
PLUGIN_DIR = ROOT / "plugins" / "g0ld2k-skills"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def safe_remove_plugin_dir() -> None:
    resolved_plugin = PLUGIN_DIR.resolve()
    resolved_plugins_root = (ROOT / "plugins").resolve()
    if resolved_plugin.parent != resolved_plugins_root:
        raise RuntimeError(f"refusing to remove unexpected path: {PLUGIN_DIR}")
    if PLUGIN_DIR.exists():
        shutil.rmtree(PLUGIN_DIR)


def copy_skills(skill_names: list[str]) -> None:
    bundled_skills_dir = PLUGIN_DIR / "skills"
    bundled_skills_dir.mkdir(parents=True, exist_ok=True)
    for skill_name in skill_names:
        source = SKILLS_DIR / skill_name
        destination = bundled_skills_dir / skill_name
        if not source.exists():
            raise FileNotFoundError(f"missing skill directory: {source}")
        shutil.copytree(source, destination)


def base_manifest(config: dict) -> dict:
    return {
        "name": config["name"],
        "description": config["description"],
        "version": config["version"],
        "author": config["author"],
        "homepage": config["homepage"],
        "repository": config["repository"],
        "license": config["license"],
        "keywords": config["keywords"],
    }


def main() -> None:
    config = json.loads(PACKAGE_CONFIG.read_text(encoding="utf-8"))
    skill_names = config["skills"]

    safe_remove_plugin_dir()
    copy_skills(skill_names)

    copilot_manifest = {
        **base_manifest(config),
        "category": config["category"],
        "skills": "./skills/",
    }
    write_json(PLUGIN_DIR / "plugin.json", copilot_manifest)

    claude_manifest = base_manifest(config)
    write_json(PLUGIN_DIR / ".claude-plugin" / "plugin.json", claude_manifest)

    codex_manifest = {
        "name": config["name"],
        "version": config["version"],
        "description": config["description"],
        "author": config["author"],
        "homepage": config["homepage"],
        "repository": config["repository"],
        "license": config["license"],
        "keywords": config["keywords"],
        "skills": "./skills/",
        "interface": {
            "displayName": "g0ld2k Skills",
            "shortDescription": "Reusable coding workflow skills",
            "longDescription": config["description"],
            "developerName": config["author"]["name"],
            "category": config["category"],
            "capabilities": [
                "Interactive",
                "Read",
                "Write"
            ],
            "defaultPrompt": [
                "Use these skills to help with pull request or release workflow.",
                "Use these skills to produce commit, PR, or review workflow output."
            ],
            "websiteURL": config["homepage"],
            "brandColor": "#2563EB",
            "screenshots": []
        }
    }
    write_json(PLUGIN_DIR / ".codex-plugin" / "plugin.json", codex_manifest)

    claude_marketplace = {
        "name": config["name"],
        "description": "Marketplace for g0ld2k reusable agent skills.",
        "owner": {
            "name": config["author"]["name"]
        },
        "plugins": [
            {
                "name": config["name"],
                "description": config["description"],
                "version": config["version"],
                "source": "./plugins/g0ld2k-skills",
                "author": config["author"]
            }
        ]
    }
    write_json(ROOT / ".claude-plugin" / "marketplace.json", claude_marketplace)

    codex_marketplace = {
        "name": config["name"],
        "interface": {
            "displayName": "g0ld2k Skills"
        },
        "plugins": [
            {
                "name": config["name"],
                "source": {
                    "source": "local",
                    "path": "./plugins/g0ld2k-skills"
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL"
                },
                "category": config["category"]
            }
        ]
    }
    write_json(ROOT / ".agents" / "plugins" / "marketplace.json", codex_marketplace)

    copilot_marketplace = {
        "name": config["name"],
        "owner": {
            "name": "g0ld2k"
        },
        "metadata": {
            "description": "Marketplace for g0ld2k reusable agent skills."
        },
        "plugins": [
            {
                "name": config["name"],
                "description": config["description"],
                "version": config["version"],
                "source": "./plugins/g0ld2k-skills"
            }
        ]
    }
    write_json(ROOT / ".github" / "plugin" / "marketplace.json", copilot_marketplace)


if __name__ == "__main__":
    main()
