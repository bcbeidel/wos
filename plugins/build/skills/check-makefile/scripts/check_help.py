#!/usr/bin/env python3
"""Tier-1 Makefile help-target checker — emits JSON ARRAY of three envelopes.

Three sub-checks:
  - help-target (WARN): a `help` target is defined.
  - help-auto (WARN):   the `help` recipe references `$(MAKEFILE_LIST)`
    and `##` (i.e., parses descriptions rather than hand-listing).
  - help-desc (WARN):   every public target (in `.PHONY` and not
    `_`-prefixed) has a `## description` suffix on its definition
    line.

Emits 3 envelopes (one per rule_id) in a JSON array, regardless of which
rules fired. Empty findings → overall_status=pass.

Exit codes: 0 on pass / warn, 64 on argument error.

Example:
    ./check_help.py path/to/Makefile
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64

_TARGET_RE = re.compile(r"^([A-Za-z0-9_./$()%-]+)\s*:(?!=)")
_PHONY_RE = re.compile(r"^\.PHONY\s*:\s*(.*)$")
_DESC_RE = re.compile(r"^[A-Za-z0-9_./$()%-]+\s*:.*##\s+\S")

_RECIPE_HELP_TARGET = (
    "Add a `help` target that parses `## description` comments from "
    "`$(MAKEFILE_LIST)`. `make help` is the user's entry point to the "
    "repo's public surface; missing it forces contributors to read the "
    "Makefile to find available commands.\n\n"
    "Example:\n"
    "    help: ## Show this help.\n"
    "    \t@awk 'BEGIN {FS = \":.*##\"} /^[a-z][a-zA-Z0-9_-]+:.*##/ \\\n"
    "    \t  { printf \"  \\033[36m%-18s\\033[0m %s\\n\", $$1, $$2 }' \\\n"
    "    \t  $(MAKEFILE_LIST)\n"
)

_RECIPE_HELP_AUTO = (
    "Replace the hand-maintained `echo` list with an `awk` parse of "
    "`$(MAKEFILE_LIST)`. Hand-maintained help rots — a new target gets "
    "added, the help list doesn't, and `make help` lies. Parsing `##` "
    "comments makes documentation a side effect of defining a target.\n\n"
    "Example:\n"
    "    help: ## Show this help.\n"
    "    \t@awk 'BEGIN {FS = \":.*##\"} /^[a-z][a-zA-Z0-9_-]+:.*##/ \\\n"
    "    \t  { printf \"  \\033[36m%-18s\\033[0m %s\\n\", $$1, $$2 }' \\\n"
    "    \t  $(MAKEFILE_LIST)\n"
)

_RECIPE_HELP_DESC = (
    "Add a `## <one-line description>` suffix to each public target "
    "definition line. Targets without `##` are invisible to the parsed "
    "`make help` output. If the target is part of the public API, "
    "document it; if it's not, rename it to `_<name>` and hide it.\n\n"
    "Example:\n"
    "    build: ## Build the project.\n"
    "    \t$(PYTHON) -m build\n"
)

_RULE_ORDER = ["help-target", "help-auto", "help-desc"]


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
            print(f"check_help.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _find_help_recipe(lines: list[str]) -> tuple[list[str] | None, int | None]:
    """Return (recipe lines of the `help:` target, line number) or (None, None)."""
    in_help = False
    recipe: list[str] = []
    help_lineno: int | None = None
    for lineno, line in enumerate(lines, 1):
        if in_help:
            if line.startswith("\t"):
                recipe.append(line)
                continue
            if not line.strip():
                continue
            break
        match = _TARGET_RE.match(line)
        if match and match.group(1) == "help":
            in_help = True
            help_lineno = lineno
    if in_help:
        return recipe, help_lineno
    return None, None


def _scan_file(
    path: Path, per_rule: dict[str, list[dict]]
) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_help.py: cannot read {path}: {err}", file=sys.stderr)
        return

    phony: set[str] = set()
    target_lines: list[tuple[str, str, int]] = []  # (name, full line, lineno)
    for lineno, line in enumerate(lines, 1):
        if line.startswith("\t"):
            continue
        phony_match = _PHONY_RE.match(line)
        if phony_match:
            for name in phony_match.group(1).split():
                phony.add(name)
            continue
        target_match = _TARGET_RE.match(line)
        if target_match:
            target_lines.append((target_match.group(1), line, lineno))

    help_recipe, help_lineno = _find_help_recipe(lines)

    # help-target
    if help_recipe is None:
        per_rule["help-target"].append(
            emit_json_finding(
                rule_id="help-target",
                status="warn",
                location={"line": 1, "context": f"{path}: no `help` target"},
                reasoning=(
                    "No `help` target defined. Without one, `make help` "
                    "fails or runs the wrong default — contributors have "
                    "no entry point to the repo's public command surface."
                ),
                recommended_changes=_RECIPE_HELP_TARGET,
            )
        )
    else:
        # help-auto — only meaningful if a help target exists
        recipe_text = "\n".join(help_recipe)
        if "$(MAKEFILE_LIST)" not in recipe_text or "##" not in recipe_text:
            per_rule["help-auto"].append(
                emit_json_finding(
                    rule_id="help-auto",
                    status="warn",
                    location={
                        "line": help_lineno or 1,
                        "context": f"{path}: hand-maintained help recipe",
                    },
                    reasoning=(
                        "`help` recipe does not parse `##` from "
                        "`$(MAKEFILE_LIST)`. Hand-maintained help rots — "
                        "a new target lands, the echo list doesn't update, "
                        "and `make help` lies."
                    ),
                    recommended_changes=_RECIPE_HELP_AUTO,
                )
            )

    # help-desc — every public phony target (not `_`-prefixed, not `help`) needs `##`
    seen: set[str] = set()
    for name, full, lineno in target_lines:
        if name in seen:
            continue
        seen.add(name)
        if name.startswith("_") or name.startswith("."):
            continue
        if name not in phony:
            continue
        if name == "help":
            continue
        if _DESC_RE.match(full):
            continue
        per_rule["help-desc"].append(
            emit_json_finding(
                rule_id="help-desc",
                status="warn",
                location={
                    "line": lineno,
                    "context": f"{path}: target `{name}` missing `## description`",
                },
                reasoning=(
                    f"Public target `{name}` has no `## description` "
                    "suffix on its definition line. Targets without "
                    "`##` are invisible to the parsed `make help` output."
                ),
                recommended_changes=_RECIPE_HELP_DESC,
            )
        )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_help.py",
        description="Tier-1 Makefile help-target checker (3 sub-checks).",
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
