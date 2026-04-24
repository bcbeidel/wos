#!/usr/bin/env python3
"""Tier-1 deterministic check: verify hook scoping directives.

For every `repo: local` hook, asserts `files:`, `types:`, or `types_or:`
is declared (WARN otherwise). For every `pass_filenames: false`
occurrence, asserts an adjacent `# justified:` comment is present on
the same or prior line (WARN otherwise).

Uses PyYAML for structured inspection and raw-text regex for the
comment-adjacency check (YAML parsers strip comments).

Exit codes: 0 clean/WARN, 2 usage error, 69 missing PyYAML, 130 interrupted.

Example:
    ./check_hook_scope.py .pre-commit-config.yaml
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

EXIT_MISSING_DEP = 69
EXIT_INTERRUPTED = 130

SCOPE_KEYS = frozenset({"files", "types", "types_or", "exclude_types"})
PASS_FILENAMES_FALSE = re.compile(r"^\s*pass_filenames:\s*false\s*(#.*)?$")
JUSTIFIED = re.compile(r"#\s*justified\b", re.IGNORECASE)


def emit(
    severity: str, path: Path, check: str, detail: str, recommendation: str
) -> None:
    print(f"{severity}  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def check_local_hook_scope(path: Path, data: dict) -> None:
    repos = data.get("repos")
    if not isinstance(repos, list):
        return
    for ri, repo in enumerate(repos):
        if not isinstance(repo, dict) or repo.get("repo") != "local":
            continue
        hooks = repo.get("hooks")
        if not isinstance(hooks, list):
            continue
        for hi, hook in enumerate(hooks):
            if not isinstance(hook, dict):
                continue
            if not SCOPE_KEYS.intersection(hook.keys()):
                hook_id = hook.get("id", f"<unnamed#{hi}>")
                emit(
                    "WARN",
                    path,
                    "hook-scope",
                    f"`repo: local` hook {hook_id!r} declares no `files:` / `types:` / `types_or:`",  # noqa: E501
                    "Add a scoping directive so the hook runs only on relevant files.",
                )


def check_pass_filenames_justification(path: Path, raw: str) -> None:
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if not PASS_FILENAMES_FALSE.match(line):
            continue
        same_line_comment = (
            "#" in line and JUSTIFIED.search(line.split("#", 1)[1]) is not None
        )
        prior_line = lines[i - 1] if i > 0 else ""
        prior_line_comment = JUSTIFIED.search(prior_line) is not None
        if not (same_line_comment or prior_line_comment):
            emit(
                "WARN",
                path,
                "pass-filenames-false",
                f"line {i + 1}: `pass_filenames: false` without adjacent `# justified:` comment",  # noqa: E501
                "Add a `# justified: <reason>` comment on the same or prior line, or remove `pass_filenames: false`.",  # noqa: E501
            )


def check_config(path: Path, yaml_mod) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml_mod.safe_load(raw)
    except (OSError, yaml_mod.YAMLError):
        return  # check_yaml_shape.py owns these FAILs
    if isinstance(data, dict):
        check_local_hook_scope(path, data)
    check_pass_filenames_justification(path, raw)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit pre-commit hook scoping directives (Tier-1 deterministic check).",  # noqa: E501
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
        for p in args.paths:
            check_config(p, yaml)
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED

    return 0  # all findings are WARN; never FAIL


if __name__ == "__main__":
    sys.exit(main())
