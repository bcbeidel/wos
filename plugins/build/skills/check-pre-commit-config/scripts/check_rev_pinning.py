#!/usr/bin/env python3
"""Tier-1 deterministic check: verify .pre-commit-config.yaml `rev:` pinning.

For every non-`local` repo, asserts:
  - `rev:` is not a floating branch name (main/master/HEAD/develop/latest/stable) — FAIL
  - `rev:` shape matches a semver tag (e.g. v1.2.3) or 40-char SHA — WARN otherwise

Emits findings in the standard lint format. Exit codes: 0 clean/WARN,
1 one or more FAIL, 2 usage error, 69 missing PyYAML, 130 interrupted.

Example:
    ./check_rev_pinning.py .pre-commit-config.yaml
"""

# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_FAIL = 1
EXIT_MISSING_DEP = 69
EXIT_INTERRUPTED = 130

FLOATING_REFS = frozenset({"main", "master", "HEAD", "develop", "latest", "stable"})
SEMVER_TAG = re.compile(r"^v?\d+\.\d+(\.\d+)?([-.].+)?$")
SHA_40 = re.compile(r"^[0-9a-f]{40}$")


def emit(
    severity: str, path: Path, check: str, detail: str, recommendation: str
) -> None:
    print(f"{severity}  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def check_config(path: Path, yaml_mod) -> int:
    """Return count of FAIL findings for this config."""
    try:
        data = yaml_mod.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml_mod.YAMLError):
        # check_yaml_shape.py owns these FAILs; stay silent here.
        return 0

    if not isinstance(data, dict):
        return 0
    repos = data.get("repos")
    if not isinstance(repos, list):
        return 0

    fails = 0
    for ri, repo in enumerate(repos):
        if not isinstance(repo, dict):
            continue
        if repo.get("repo") == "local":
            continue
        rev = repo.get("rev")
        if not isinstance(rev, str):
            continue  # missing/non-string rev — check_yaml_shape / pre-commit itself will flag  # noqa: E501

        if rev in FLOATING_REFS:
            emit(
                "FAIL",
                path,
                "floating-rev",
                f"repos[{ri}] rev: {rev!r} is a floating ref",
                "Pin to an immutable tag or 40-char SHA. `pre-commit autoupdate` pins the current stable tag.",  # noqa: E501
            )
            fails += 1
            continue

        if not (SEMVER_TAG.match(rev) or SHA_40.match(rev)):
            emit(
                "WARN",
                path,
                "rev-shape",
                f"repos[{ri}] rev: {rev!r} is neither semver tag nor 40-char SHA",
                "Resolve to a versioned tag (vX.Y.Z) or a full 40-char commit SHA for stronger immutability.",  # noqa: E501
            )

    return fails


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit .pre-commit-config.yaml `rev:` pins (Tier-1 deterministic check).",  # noqa: E501
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
