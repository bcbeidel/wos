"""Tests for version consistency across configuration files."""

from __future__ import annotations

import json
from pathlib import Path


def _project_root() -> Path:
    """Return the project root directory (parent of tests/)."""
    return Path(__file__).resolve().parent.parent


def test_version_consistent_across_config_files() -> None:
    """pyproject.toml, plugin.json, and marketplace.json must have matching versions."""
    root = _project_root()

    # pyproject.toml
    pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_version = None
    for line in pyproject_text.splitlines():
        if line.strip().startswith("version"):
            pyproject_version = line.split("=", 1)[1].strip().strip('"')
            break
    assert pyproject_version is not None, "No version found in pyproject.toml"

    # plugin.json
    plugin_data = json.loads(
        (root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    plugin_version = plugin_data["version"]

    # marketplace.json
    marketplace_data = json.loads(
        (root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    marketplace_version = marketplace_data["plugins"][0]["version"]

    assert pyproject_version == plugin_version, (
        f"pyproject.toml ({pyproject_version}) != "
        f"plugin.json ({plugin_version})"
    )
    assert pyproject_version == marketplace_version, (
        f"pyproject.toml ({pyproject_version}) != "
        f"marketplace.json ({marketplace_version})"
    )
