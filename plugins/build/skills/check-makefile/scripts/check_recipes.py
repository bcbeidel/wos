#!/usr/bin/env python3
"""Tier-1 Makefile recipe-hygiene checker — emits JSON ARRAY of four envelopes.

Four rules scanning recipe lines (tab-indented):
  - literal-make (WARN):     bare `make` (not `$(MAKE)`) as a command
                             token.
  - at-discipline (WARN):    `@`-prefix only on `echo`, `printf`, `:`,
                             `true`, `#`, `awk`, `sed`.
  - or-true-guard (WARN):    `|| true` without an adjacent explanatory
                             comment (same line or previous non-blank
                             line).
  - recipe-length (WARN):    any target's recipe exceeds 10 lines.

Exit codes:
  0  — overall_status pass / warn for every emitted envelope
  1  — overall_status=fail (none in this script)
  64 — usage error

Example:
    ./check_recipes.py path/to/Makefile
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
PROG = "check_recipes.py"
MAX_RECIPE_LINES = 10

_TARGET_RE = re.compile(r"^([A-Za-z0-9_./$()%-]+)\s*:(?!=)")
_LITERAL_MAKE_RE = re.compile(r"(?:^|[;&|\s])make(?!FLAGS|FILE)\b")
_AT_PREFIX_RE = re.compile(r"^\t@(\S+)")
_OR_TRUE_RE = re.compile(r"\|\|\s*true\b")
_INLINE_COMMENT_RE = re.compile(r"#[^\n]*")

_AT_ALLOWED_CMDS = ("echo", "printf", ":", "true", "#", "awk", "sed")

_RECIPE_LITERAL_MAKE = (
    "Replace bare `make` with `$(MAKE)` — or remove the recursion "
    "entirely if a flat target graph works. `$(MAKE)` propagates `-j`, "
    "`-s`, `MAKEFLAGS`, and Make's internal state; bare `make` spawns "
    "a fresh Make that knows none of that.\n\n"
    "Example (flat graph, preferred):\n"
    "    ci: lint test\n"
    "\n"
    "Example (recursion, when needed):\n"
    "    ci:\n"
    "    \t$(MAKE) lint\n"
    "    \t$(MAKE) test\n"
)

_RECIPE_AT_DISCIPLINE = (
    "Remove `@` unless the command is `echo`, `printf`, or `:`. Hiding "
    "the command obscures what is running when something fails. Users "
    "who want quiet output run `make -s`. `@` stays legitimate on "
    "`echo` / `printf` where the output is the command.\n\n"
    "Example:\n"
    "    test:\n"
    "    \t@echo 'Running tests...'    # @ ok — output is the message\n"
    "    \t$(PYTHON) -m pytest         # no @ — show what we ran\n"
)

_RECIPE_OR_TRUE_GUARD = (
    "Either remove `|| true` (let the failure propagate) or annotate "
    "with a comment explaining why failure is acceptable. Silent error "
    "suppression is how broken builds ship.\n\n"
    "Example:\n"
    "    cleanup:\n"
    "    \t# || true is intentional — $(BUILD_DIR) may not exist on a clean checkout.\n"
    "    \trm -rf -- \"$(BUILD_DIR)\" || true\n"
)

_RECIPE_RECIPE_LENGTH = (
    "Extract the recipe body into `scripts/<name>.sh` and invoke from "
    "the target. A `scripts/deploy.sh` can be `shellcheck`'d, "
    "unit-tested, and invoked independently. Make is a poor scripting "
    "language.\n\n"
    "Example:\n"
    "    deploy: ## Deploy to production (set CONFIRM=1).\n"
    "    \t@[[ \"$${CONFIRM:-0}\" = \"1\" ]] || { echo 'set CONFIRM=1' >&2; exit 1; }\n"
    "    \t./scripts/deploy.sh\n"
)

_RULE_ORDER = ["literal-make", "at-discipline", "or-true-guard", "recipe-length"]


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


def _has_adjacent_comment(lines: list[str], idx: int) -> bool:
    if _INLINE_COMMENT_RE.search(lines[idx]):
        return True
    for i in range(idx - 1, -1, -1):
        if not lines[i].strip():
            continue
        return bool(_INLINE_COMMENT_RE.search(lines[i]))
    return False


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"{PROG}: cannot read {path}: {err}", file=sys.stderr)
        return

    current_target: str | None = None
    current_target_line: int = 0
    recipe_count = 0

    def _flush(name: str | None, count: int, target_line: int) -> None:
        if name is not None and count > MAX_RECIPE_LINES:
            per_rule["recipe-length"].append(
                emit_json_finding(
                    rule_id="recipe-length",
                    status="warn",
                    location={
                        "line": target_line,
                        "context": f"{path}: target {name!r} ({count} recipe lines)",
                    },
                    reasoning=(
                        f"target {name!r} has {count} recipe lines, exceeding "
                        f"the {MAX_RECIPE_LINES}-line cap. Long recipes are "
                        "untestable and unreadable; extract to scripts/."
                    ),
                    recommended_changes=_RECIPE_RECIPE_LENGTH,
                )
            )

    for idx, line in enumerate(lines):
        lineno = idx + 1

        # Track target boundaries
        if not line.startswith("\t"):
            _flush(current_target, recipe_count, current_target_line)
            if not line.strip():
                current_target = None
                recipe_count = 0
                continue
            match = _TARGET_RE.match(line)
            if match and not line.startswith("."):
                current_target = match.group(1)
                current_target_line = lineno
                recipe_count = 0
            else:
                current_target = None
                recipe_count = 0
            continue

        if current_target is not None:
            recipe_count += 1

        # Strip comments before matching literal-make (avoid false hits in `# run make`)
        stripped = _INLINE_COMMENT_RE.sub("", line)

        # literal-make: avoid $(MAKE) / ${MAKE}
        probe = stripped.replace("$(MAKE)", "").replace("${MAKE}", "")
        if _LITERAL_MAKE_RE.search(probe):
            per_rule["literal-make"].append(
                emit_json_finding(
                    rule_id="literal-make",
                    status="warn",
                    location={
                        "line": lineno,
                        "context": f"{path}: {line.strip()[:80]}",
                    },
                    reasoning=(
                        f"line {lineno}: bare `make` in recipe. Bare `make` "
                        "spawns a fresh Make that loses `-j`, `-s`, and "
                        "`MAKEFLAGS`; use `$(MAKE)` or a flat target graph."
                    ),
                    recommended_changes=_RECIPE_LITERAL_MAKE,
                )
            )

        at_match = _AT_PREFIX_RE.match(line)
        if at_match:
            cmd = at_match.group(1).strip()
            cmd_head = cmd.split("$", 1)[0]  # strip $(VAR) suffixes
            cmd_head = cmd_head.split("(", 1)[0] or cmd_head
            if not any(cmd_head.startswith(allowed) for allowed in _AT_ALLOWED_CMDS):
                per_rule["at-discipline"].append(
                    emit_json_finding(
                        rule_id="at-discipline",
                        status="warn",
                        location={
                            "line": lineno,
                            "context": f"{path}: @{cmd[:60]}",
                        },
                        reasoning=(
                            f"line {lineno}: `@`-prefixed `{cmd[:40]}` is "
                            "not echo/printf/:. Hiding the command obscures "
                            "failures; users who want quiet output run "
                            "`make -s`."
                        ),
                        recommended_changes=_RECIPE_AT_DISCIPLINE,
                    )
                )

        if _OR_TRUE_RE.search(stripped) and not _has_adjacent_comment(lines, idx):
            per_rule["or-true-guard"].append(
                emit_json_finding(
                    rule_id="or-true-guard",
                    status="warn",
                    location={
                        "line": lineno,
                        "context": f"{path}: {line.strip()[:80]}",
                    },
                    reasoning=(
                        f"line {lineno}: `|| true` without an adjacent "
                        "explanatory comment. Silent error suppression is "
                        "how broken builds ship."
                    ),
                    recommended_changes=_RECIPE_OR_TRUE_GUARD,
                )
            )

    # Flush trailing target
    _flush(current_target, recipe_count, current_target_line)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG, description="Tier-1 Makefile recipe-hygiene checker (4 rules)."
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
