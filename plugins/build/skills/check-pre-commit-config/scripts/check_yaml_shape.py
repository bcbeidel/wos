#!/usr/bin/env python3
"""Tier-1 deterministic check: validate .pre-commit-config.yaml shape.

Verifies the file exists, parses as YAML, has a non-empty top-level
`repos:` list, and every hook entry is a mapping with a string `id:`.

Emits findings in the standard lint format:
    SEVERITY  <path> — <check>: <detail>
    Recommendation: <change>

Exit codes:
    0    clean
    1    one or more FAIL findings
    2    usage error (argparse)
    69   missing required dependency (PyYAML)
    130  interrupted

Example:
    ./check_yaml_shape.py .pre-commit-config.yaml
"""

# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///

from __future__ import annotations

import argparse
import sys
from pathlib import Path

EXIT_FAIL = 1
EXIT_MISSING_DEP = 69
EXIT_INTERRUPTED = 130


def emit(
    severity: str, path: Path, check: str, detail: str, recommendation: str
) -> None:
    print(f"{severity}  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def check_config(path: Path, yaml_mod) -> int:
    """Run all shape checks on one config path. Return count of FAIL findings."""
    if not path.exists():
        emit(
            "FAIL",
            path,
            "config-missing",
            f".pre-commit-config.yaml not found at {path}",
            "Run `/build:build-pre-commit-config` to scaffold a config.",
        )
        return 1

    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml_mod.safe_load(raw)
    except yaml_mod.YAMLError as err:
        emit(
            "FAIL",
            path,
            "yaml-parse",
            f"YAML parse error: {err}",
            "Fix the syntax error; check for mixed tabs/spaces, unquoted leading *, unbalanced brackets.",  # noqa: E501
        )
        return 1
    except OSError as err:
        emit(
            "FAIL",
            path,
            "config-missing",
            f"cannot read config: {err}",
            "Verify the file exists and is readable.",
        )
        return 1

    fails = 0

    if not isinstance(data, dict):
        emit(
            "FAIL",
            path,
            "yaml-parse",
            "top-level YAML is not a mapping",
            "The config must be a YAML mapping with at least a `repos:` key.",
        )
        return 1

    repos = data.get("repos")
    if not isinstance(repos, list) or not repos:
        emit(
            "FAIL",
            path,
            "repos-key",
            "top-level `repos:` key missing or empty",
            "Add a `repos:` list with at least one repo block.",
        )
        return 1

    for ri, repo in enumerate(repos):
        if not isinstance(repo, dict):
            emit(
                "FAIL",
                path,
                "hook-shape",
                f"repos[{ri}] is not a mapping",
                "Each repo entry must be a YAML mapping with `repo:` and `hooks:` keys.",  # noqa: E501
            )
            fails += 1
            continue

        hooks = repo.get("hooks")
        if not isinstance(hooks, list):
            emit(
                "FAIL",
                path,
                "hook-shape",
                f"repos[{ri}] has no `hooks:` list",
                "Add a `hooks:` list to this repo block.",
            )
            fails += 1
            continue

        for hi, hook in enumerate(hooks):
            if not isinstance(hook, dict):
                emit(
                    "FAIL",
                    path,
                    "hook-shape",
                    f"repos[{ri}].hooks[{hi}] is not a mapping",
                    "Each hook entry must be a YAML mapping with at least an `id:` key.",  # noqa: E501
                )
                fails += 1
                continue
            hook_id = hook.get("id")
            if not isinstance(hook_id, str) or not hook_id.strip():
                emit(
                    "FAIL",
                    path,
                    "hook-shape",
                    f"repos[{ri}].hooks[{hi}] missing string `id:`",
                    "Add a kebab-case `id:` naming what the hook does.",
                )
                fails += 1

    return fails


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate .pre-commit-config.yaml shape (Tier-1 deterministic check).",  # noqa: E501
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more paths to .pre-commit-config.yaml files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)

    try:
        import yaml
    except ImportError:
        print(
            "error: PyYAML required. Install via `pip install pyyaml`.",
            file=sys.stderr,
        )
        return EXIT_MISSING_DEP

    try:
        total = sum(check_config(p, yaml) for p in args.paths)
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED

    return EXIT_FAIL if total else 0


if __name__ == "__main__":
    sys.exit(main())
