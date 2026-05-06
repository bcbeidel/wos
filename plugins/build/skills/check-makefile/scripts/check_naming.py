#!/usr/bin/env python3
"""Tier-1 Makefile naming checker — emits JSON ARRAY of two envelopes.

Two rules:
  - target-name (WARN):    public target names (those with a `##`
                           description) match `^[a-z][a-z0-9-]*$`.
  - helper-prefix (WARN):  targets without a `##` description, without
                           a `_` prefix, and without file indicators
                           (`/`, `.`, `%`, `$(`, `${`) — likely
                           helpers that should start with `_`.

Severity floor: WARN. (helper-prefix was previously INFO.)

Exit codes:
  0  — overall_status pass / warn for every emitted envelope
  1  — overall_status=fail (none in this script)
  64 — usage error

Example:
    ./check_naming.py path/to/Makefile
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
PROG = "check_naming.py"

_TARGET_RE = re.compile(r"^([A-Za-z0-9_./$()%-]+)\s*:(?!=)")
_DESC_RE = re.compile(r"^[A-Za-z0-9_./$()%-]+\s*:.*##\s+\S")
_PUBLIC_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_FILE_INDICATORS = ("/", ".", "$(", "${", "%")

_RECIPE_TARGET_NAME = (
    "Rename to lowercase-hyphenated shape `^[a-z][a-z0-9-]*$` (e.g., "
    "`run-tests`, not `runTheTests`; `build-prod`, not `build_prod`; "
    "`deploy`, not `Deploy`). Muscle memory for `make test` / `make "
    "build` works across repos only when names follow the shell-command "
    "convention.\n\n"
    "Example:\n"
    "    run-tests: ## Run the test suite.\n"
    "    build-prod: ## Build the production artifact.\n"
)

_RECIPE_HELPER_PREFIX = (
    "Rename the helper target to `_<name>` and omit the `##`. The "
    "underscore prefix signals 'not part of the public API' to both "
    "readers and the `help` parser; it keeps `make help` clean.\n\n"
    "Example:\n"
    "    _check-deps:\n"
    "    \t@command -v jq >/dev/null || { echo 'jq required' >&2; exit 1; }\n"
    "    \n"
    "    test: _check-deps ## Run the test suite.\n"
    "    \t$(PYTHON) -m pytest\n"
)

_RULE_ORDER = ["target-name", "helper-prefix"]


class _UsageError(Exception):
    pass


def _is_makefile(path: Path) -> bool:
    return path.name in ("Makefile", "GNUmakefile") or path.suffix == ".mk"


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_makefile(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_makefile(child):
                    files.append(child)
        else:
            print(f"{PROG}: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"{PROG}: cannot read {path}: {err}", file=sys.stderr)
        return

    seen: set[str] = set()

    for lineno, line in enumerate(lines, 1):
        if line.startswith("\t"):
            continue
        match = _TARGET_RE.match(line)
        if not match:
            continue
        name = match.group(1)
        if name in seen or name.startswith("."):
            continue
        seen.add(name)
        has_desc = bool(_DESC_RE.match(line))
        has_file_indicator = any(ind in name for ind in _FILE_INDICATORS)

        if has_desc:
            if not _PUBLIC_NAME_RE.match(name):
                per_rule["target-name"].append(
                    emit_json_finding(
                        rule_id="target-name",
                        status="warn",
                        location={
                            "line": lineno,
                            "context": f"{path}: target {name!r}",
                        },
                        reasoning=(
                            f"public target {name!r} does not match "
                            "`^[a-z][a-z0-9-]*$`. PascalCase / snake_case / "
                            "camelCase break the muscle-memory convention "
                            "for `make <verb>`."
                        ),
                        recommended_changes=_RECIPE_TARGET_NAME,
                    )
                )
        else:
            if not has_file_indicator and not name.startswith("_"):
                per_rule["helper-prefix"].append(
                    emit_json_finding(
                        rule_id="helper-prefix",
                        status="warn",
                        location={
                            "line": lineno,
                            "context": f"{path}: target {name!r}",
                        },
                        reasoning=(
                            f"target {name!r} has no `##` description and is "
                            "not prefixed with `_`. If it is an internal "
                            "helper, the `_` prefix hides it from `make "
                            "help`; if it is public, it needs a `##`."
                        ),
                        recommended_changes=_RECIPE_HELPER_PREFIX,
                    )
                )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG, description="Tier-1 Makefile naming checker (2 rules)."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more Makefile / *.mk files or directories (non-recursive).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        files = _collect_targets(args.paths)
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130

    per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
    for f in files:
        _scan_file(f, per_rule)

    envelopes = [
        emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in _RULE_ORDER
    ]
    print_envelope(envelopes)
    any_fail = any(e["overall_status"] == "fail" for e in envelopes)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
