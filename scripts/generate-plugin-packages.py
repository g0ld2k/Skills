#!/usr/bin/env python3
"""Generate product plugin manifests and bundled skill copies."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGING_DIR = ROOT / "packaging"
SKILLS_DIR = ROOT / "skills"
PLUGINS_DIR = ROOT / "plugins"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_package_configs() -> list[dict]:
    configs: list[dict] = []
    for path in sorted(PACKAGING_DIR.glob("*.json")):
        config = json.loads(path.read_text(encoding="utf-8"))
        if config.get("name") != path.stem:
            raise ValueError(f"package name must match config filename: {path}")
        configs.append(config)
    if not configs:
        raise FileNotFoundError(f"no plugin package configs found in {PACKAGING_DIR}")
    return sorted(configs, key=lambda config: ("marketplace" not in config, config["name"]))


def plugin_dir(config: dict) -> Path:
    return PLUGINS_DIR / config["name"]


def safe_remove_plugin_dir(config: dict) -> None:
    destination = plugin_dir(config)
    resolved_plugin = destination.resolve()
    resolved_plugins_root = PLUGINS_DIR.resolve()
    if resolved_plugin.parent != resolved_plugins_root:
        raise RuntimeError(f"refusing to remove unexpected path: {destination}")
    if destination.exists():
        shutil.rmtree(destination)


def copy_skills(config: dict) -> None:
    bundled_skills_dir = plugin_dir(config) / "skills"
    bundled_skills_dir.mkdir(parents=True, exist_ok=True)
    if not config["skills"]:
        (bundled_skills_dir / ".gitkeep").write_text("", encoding="utf-8")
    for skill_name in config["skills"]:
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


def generate_plugin(config: dict) -> None:
    destination = plugin_dir(config)
    interface = config["interface"]

    safe_remove_plugin_dir(config)
    copy_skills(config)

    copilot_manifest = {
        **base_manifest(config),
        "category": config["category"],
        "skills": "./skills/",
    }
    write_json(destination / "plugin.json", copilot_manifest)

    claude_manifest = base_manifest(config)
    write_json(destination / ".claude-plugin" / "plugin.json", claude_manifest)

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
            "displayName": interface["display_name"],
            "shortDescription": interface["short_description"],
            "longDescription": config["description"],
            "developerName": config["author"]["name"],
            "category": config["category"],
            "capabilities": interface["capabilities"],
            "defaultPrompt": interface["default_prompts"],
            "websiteURL": config["homepage"],
            "brandColor": interface["brand_color"],
            "screenshots": []
        }
    }
    write_json(destination / ".codex-plugin" / "plugin.json", codex_manifest)


def generate_marketplaces(configs: list[dict]) -> None:
    marketplace_configs = [config for config in configs if "marketplace" in config]
    if len(marketplace_configs) != 1:
        raise ValueError("exactly one package config must define marketplace metadata")
    marketplace = marketplace_configs[0]["marketplace"]

    claude_marketplace = {
        "name": marketplace["name"],
        "description": marketplace["description"],
        "owner": {
            "name": marketplace["owner_name"]
        },
        "plugins": [
            {
                "name": config["name"],
                "description": config["description"],
                "version": config["version"],
                "source": f"./plugins/{config['name']}",
                "author": config["author"]
            }
            for config in configs
        ]
    }
    write_json(ROOT / ".claude-plugin" / "marketplace.json", claude_marketplace)

    codex_marketplace = {
        "name": marketplace["name"],
        "interface": {
            "displayName": marketplace["display_name"]
        },
        "plugins": [
            {
                "name": config["name"],
                "source": {
                    "source": "local",
                    "path": f"./plugins/{config['name']}"
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL"
                },
                "category": config["category"]
            }
            for config in configs
        ]
    }
    write_json(ROOT / ".agents" / "plugins" / "marketplace.json", codex_marketplace)

    copilot_marketplace = {
        "name": marketplace["name"],
        "owner": {
            "name": marketplace["github_owner"]
        },
        "metadata": {
            "description": marketplace["description"]
        },
        "plugins": [
            {
                "name": config["name"],
                "description": config["description"],
                "version": config["version"],
                "source": f"./plugins/{config['name']}"
            }
            for config in configs
        ]
    }
    write_json(ROOT / ".github" / "plugin" / "marketplace.json", copilot_marketplace)


def main() -> None:
    configs = load_package_configs()
    for config in configs:
        generate_plugin(config)
    generate_marketplaces(configs)


if __name__ == "__main__":
    main()
