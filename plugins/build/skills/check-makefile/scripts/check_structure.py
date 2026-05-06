#!/usr/bin/env python3
"""Tier-1 Makefile structural checker — emits JSON ARRAY of seven envelopes.

Seven orthogonal structural sub-checks against each target:
  - shell-pin (FAIL):       `SHELL := bash` (or `/bin/bash`).
  - shellflags (FAIL):      `.SHELLFLAGS` has `-e`, `-o pipefail`, `-c`.
  - warn-undefined (WARN):  `MAKEFLAGS += --warn-undefined-variables`.
  - no-builtin-rules (WARN): `MAKEFLAGS += --no-builtin-rules` or
    a bare `.SUFFIXES:` line.
  - delete-on-error (WARN): `.DELETE_ON_ERROR:` present.
  - default-goal (WARN):    `.DEFAULT_GOAL := help` or `help` is the
    first non-pattern target.
  - header-comment (WARN):  comment block in first 5 non-blank lines
    naming project / requirements.

Emits 7 envelopes (one per rule_id) in a JSON array, regardless of which
rules fired. Empty findings → overall_status=pass.

Exit codes:
  0  — overall_status pass / warn for every emitted envelope
  1  — overall_status=fail (shell-pin or shellflags failures)
  64 — usage error

Example:
    ./check_structure.py path/to/Makefile path/to/mk/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
HEADER_WINDOW = 5
MIN_HEADER_COMMENTS = 2

_SHELL_RE = re.compile(r"^SHELL\s*[:?]?=\s*(?:/bin/)?bash\b")
_SHELLFLAGS_RE = re.compile(r"^\.SHELLFLAGS\s*[:?]?=\s*(.+)$")
_WARN_UNDEF_RE = re.compile(r"MAKEFLAGS\s*\+?=.*--warn-undefined-variables")
_NO_BUILTIN_RE = re.compile(r"MAKEFLAGS\s*\+?=.*--no-builtin-rules")
_SUFFIXES_RE = re.compile(r"^\.SUFFIXES\s*:\s*$")
_DELETE_ON_ERROR_RE = re.compile(r"^\.DELETE_ON_ERROR\s*:")
_DEFAULT_GOAL_HELP_RE = re.compile(r"^\.DEFAULT_GOAL\s*:?=\s*help\b")
_TARGET_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_./$()%-]*)\s*:(?!=)")

_RECIPE_SHELL_PIN = (
    "Add `SHELL := bash` near the top of the Makefile (above any recipe). "
    "Default `/bin/sh` varies across systems (dash on Debian, bash on older "
    "Red Hat, ash on Alpine); pinning bash locks the dialect so `pipefail`, "
    "`[[ ]]`, and other bashisms work predictably.\n\n"
    "Example:\n"
    "    SHELL := bash\n"
)

_RECIPE_SHELLFLAGS = (
    "Set `.SHELLFLAGS := -eu -o pipefail -c`. Without `pipefail`, a failing "
    "`curl | jq` silently succeeds if `jq` exits 0. Without `-e`, a failing "
    "intermediate command lets the recipe continue. `-u` catches "
    "undefined-variable typos in recipes.\n\n"
    "Example:\n"
    "    SHELL := bash\n"
    "    .SHELLFLAGS := -eu -o pipefail -c\n"
)

_RECIPE_WARN_UNDEFINED = (
    "Add `MAKEFLAGS += --warn-undefined-variables` to catch typos that would "
    "otherwise expand to empty. A typo like `$(BULID_DIR)` expands to empty; "
    "`rm -rf $(BUILD_DIR)/` then turns into `rm -rf /`. Make catches the typo "
    "only with this flag set.\n\n"
    "Example:\n"
    "    MAKEFLAGS += --warn-undefined-variables\n"
)

_RECIPE_NO_BUILTIN_RULES = (
    "Add `MAKEFLAGS += --no-builtin-rules` and/or a bare `.SUFFIXES:` line to "
    "disable legacy implicit rules. Built-in rules (C compilation, Fortran, "
    "RCS/SCCS checkout) predate modern workflows — `make foo` may "
    "\"just work\" because a `foo.c` nearby triggers `%.o: %.c`. Disabling "
    "removes the surprise.\n\n"
    "Example:\n"
    "    MAKEFLAGS += --no-builtin-rules\n"
    "    .SUFFIXES:\n"
)

_RECIPE_DELETE_ON_ERROR = (
    "Add a bare `.DELETE_ON_ERROR:` line. Without this, a recipe that writes "
    "to `$@` and then fails leaves a truncated file on disk. Make thinks the "
    "target is built on the next run and skips it. Enabling it makes Make "
    "delete the target on recipe failure.\n\n"
    "Example:\n"
    "    .DELETE_ON_ERROR:\n"
)

_RECIPE_DEFAULT_GOAL = (
    "Add `.DEFAULT_GOAL := help` near the top, or reorder so `help` is the "
    "first non-pattern target. Bare `make` defaulting to a build is a "
    "footgun — contributors hit Enter expecting docs and get a ten-minute "
    "build. Defaulting to `help` preserves the no-surprise invariant.\n\n"
    "Example:\n"
    "    .DEFAULT_GOAL := help\n"
    "\n"
    "    help: ## Show this help.\n"
    "    \t@awk 'BEGIN {FS = \":.*##\"} /^[a-z][a-zA-Z0-9_-]+:.*##/ \\\n"
    "    \t  { printf \"  \\033[36m%-18s\\033[0m %s\\n\", $$1, $$2 }' \\\n"
    "    \t  $(MAKEFILE_LIST)\n"
)

_RECIPE_HEADER_COMMENT = (
    "Add a header comment in the first 5 non-blank lines naming the project "
    "and environment requirements (e.g., GNU Make >= 4.0, bash). The header "
    "is the first thing a reader sees; a file without one is opaque to "
    "anyone who isn't the author.\n\n"
    "Example:\n"
    "    # repo-name — developer workflow orchestration.\n"
    "    # Requires: GNU Make >= 4.0, bash.\n"
    "\n"
    "    SHELL := bash\n"
)

_RULE_ORDER = [
    "shell-pin",
    "shellflags",
    "warn-undefined",
    "no-builtin-rules",
    "delete-on-error",
    "default-goal",
    "header-comment",
]


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
            print(f"check_structure.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _shellflags_ok(rhs: str) -> bool:
    return "-e" in rhs and "pipefail" in rhs and "-c" in rhs


def _first_non_pattern_target(lines: list[str]) -> str | None:
    for line in lines:
        if line.startswith("\t") or line.startswith("#") or not line.strip():
            continue
        if line.startswith("."):
            continue
        match = _TARGET_RE.match(line)
        if match:
            name = match.group(1)
            if "%" not in name:
                return name
    return None


def _header_has_comments(lines: list[str]) -> bool:
    count = 0
    seen = 0
    for line in lines:
        if not line.strip():
            continue
        seen += 1
        if line.lstrip().startswith("#"):
            count += 1
        if seen >= HEADER_WINDOW:
            break
    return count >= MIN_HEADER_COMMENTS


def _scan_shell_pin(path: Path, lines: list[str]) -> list[dict]:
    if any(_SHELL_RE.match(line) for line in lines):
        return []
    return [
        emit_json_finding(
            rule_id="shell-pin",
            status="fail",
            location={"line": 1, "context": f"{path}: SHELL not pinned to bash"},
            reasoning=(
                "`SHELL := bash` (or `/bin/bash`) not found. Default `/bin/sh` "
                "varies across systems and silently breaks bashisms like "
                "`pipefail` and `[[ ]]`."
            ),
            recommended_changes=_RECIPE_SHELL_PIN,
        )
    ]


def _scan_shellflags(path: Path, lines: list[str]) -> list[dict]:
    shellflags_match = next(
        (_SHELLFLAGS_RE.match(line) for line in lines if _SHELLFLAGS_RE.match(line)),
        None,
    )
    if not shellflags_match:
        return [
            emit_json_finding(
                rule_id="shellflags",
                status="fail",
                location={"line": 1, "context": f"{path}: .SHELLFLAGS missing"},
                reasoning=(
                    "`.SHELLFLAGS` assignment missing. Without `-e -o pipefail "
                    "-c`, failing pipeline stages and intermediate commands "
                    "do not propagate exit codes — silent failures ship."
                ),
                recommended_changes=_RECIPE_SHELLFLAGS,
            )
        ]
    if not _shellflags_ok(shellflags_match.group(1)):
        return [
            emit_json_finding(
                rule_id="shellflags",
                status="fail",
                location={
                    "line": 1,
                    "context": f"{path}: .SHELLFLAGS missing -e / -o pipefail / -c",
                },
                reasoning=(
                    "`.SHELLFLAGS` is set but missing one of `-e`, `-o pipefail`, "
                    "or `-c`. All three are required for safe recipe execution."
                ),
                recommended_changes=_RECIPE_SHELLFLAGS,
            )
        ]
    return []


def _scan_warn_undefined(path: Path, lines: list[str]) -> list[dict]:
    if any(_WARN_UNDEF_RE.search(line) for line in lines):
        return []
    return [
        emit_json_finding(
            rule_id="warn-undefined",
            status="warn",
            location=None,
            reasoning=(
                "`MAKEFLAGS += --warn-undefined-variables` missing. A typo "
                "like `$(BULID_DIR)` expands to empty silently — without this "
                "flag, `rm -rf $(BUILD_DIR)/` can become `rm -rf /`."
            ),
            recommended_changes=_RECIPE_WARN_UNDEFINED,
        )
    ]


def _scan_no_builtin_rules(path: Path, lines: list[str]) -> list[dict]:
    has_nobuiltin = any(_NO_BUILTIN_RE.search(line) for line in lines)
    has_suffixes = any(_SUFFIXES_RE.match(line) for line in lines)
    if has_nobuiltin or has_suffixes:
        return []
    return [
        emit_json_finding(
            rule_id="no-builtin-rules",
            status="warn",
            location=None,
            reasoning=(
                "Neither `MAKEFLAGS += --no-builtin-rules` nor a bare "
                "`.SUFFIXES:` line is present. Built-in implicit rules "
                "(C compilation, Fortran, RCS/SCCS) produce surprising "
                "behavior in modern workflows."
            ),
            recommended_changes=_RECIPE_NO_BUILTIN_RULES,
        )
    ]


def _scan_delete_on_error(path: Path, lines: list[str]) -> list[dict]:
    if any(_DELETE_ON_ERROR_RE.match(line) for line in lines):
        return []
    return [
        emit_json_finding(
            rule_id="delete-on-error",
            status="warn",
            location=None,
            reasoning=(
                "`.DELETE_ON_ERROR:` missing. A recipe that writes to `$@` "
                "then fails leaves a truncated file on disk; Make thinks the "
                "target is built next run and skips it."
            ),
            recommended_changes=_RECIPE_DELETE_ON_ERROR,
        )
    ]


def _scan_default_goal(path: Path, lines: list[str]) -> list[dict]:
    has_default_goal = any(_DEFAULT_GOAL_HELP_RE.match(line) for line in lines)
    first_target = _first_non_pattern_target(lines)
    if has_default_goal or first_target == "help":
        return []
    return [
        emit_json_finding(
            rule_id="default-goal",
            status="warn",
            location=None,
            reasoning=(
                "`.DEFAULT_GOAL := help` missing and `help` is not the first "
                "non-pattern target. Bare `make` defaulting to a build is a "
                "footgun — contributors hit Enter expecting docs and get a "
                "long-running build."
            ),
            recommended_changes=_RECIPE_DEFAULT_GOAL,
        )
    ]


def _scan_header_comment(path: Path, lines: list[str]) -> list[dict]:
    if _header_has_comments(lines):
        return []
    return [
        emit_json_finding(
            rule_id="header-comment",
            status="warn",
            location={"line": 1, "context": f"{path}: header window"},
            reasoning=(
                f"Fewer than {MIN_HEADER_COMMENTS} comment lines in the "
                f"first {HEADER_WINDOW} non-blank lines. Without a header "
                "block, a reader cannot see the project name or environment "
                "requirements (e.g., GNU Make version, bash)."
            ),
            recommended_changes=_RECIPE_HEADER_COMMENT,
        )
    ]


_SCANNERS = {
    "shell-pin": _scan_shell_pin,
    "shellflags": _scan_shellflags,
    "warn-undefined": _scan_warn_undefined,
    "no-builtin-rules": _scan_no_builtin_rules,
    "delete-on-error": _scan_delete_on_error,
    "default-goal": _scan_default_goal,
    "header-comment": _scan_header_comment,
}


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_structure.py: cannot read {path}: {err}", file=sys.stderr)
        return
    for rule_id in _RULE_ORDER:
        per_rule[rule_id].extend(_SCANNERS[rule_id](path, lines))


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_structure.py",
        description="Tier-1 Makefile structural checker (7 sub-checks).",
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
