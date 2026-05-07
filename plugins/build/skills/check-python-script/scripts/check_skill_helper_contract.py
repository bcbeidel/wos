#!/usr/bin/env python3
"""Tier-1 skill-helper-profile checks. Emits JSON ARRAY of three envelopes.

Three rules:
  - skill-helper-stdin-json (FAIL): the script does not read a JSON
    payload from stdin. Required pattern is `json.loads(sys.stdin.read())`
    or `json.load(sys.stdin)`.
  - skill-helper-atomic-write (WARN): the script writes to files but
    does not use the `<path>.tmp` + `os.replace` atomic-write pattern.
  - skill-helper-distinct-error-codes (WARN): the script may exit
    non-zero but does not declare distinct error codes (e.g.,
    `EXIT_USER_ERROR = 2` and `EXIT_INTERNAL_ERROR = 3`).

Usage:
    check_skill_helper_contract.py <path> [<path> ...]

Exit codes:
    0  no FAIL findings
    1  one or more FAIL findings
    64 usage error
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_CLEAN = 0
EXIT_FAIL = 1
EXIT_USAGE = 64

RULE_STDIN_JSON = "skill-helper-stdin-json"
RULE_ATOMIC_WRITE = "skill-helper-atomic-write"
RULE_EXIT_CODES = "skill-helper-distinct-error-codes"

RECIPE_STDIN_JSON = (
    "Read the payload from stdin via "
    "`payload = json.loads(sys.stdin.read())`. The skill-helper "
    "contract is JSON over stdio — do not accept payload through "
    "CLI flags."
)
RECIPE_ATOMIC_WRITE = (
    "When writing files, use the atomic-write pattern: "
    "`tmp = path.with_suffix(path.suffix + '.tmp'); "
    "tmp.write_text(content); os.replace(tmp, path)`. Direct "
    "`path.write_text(...)` may leave half-written state on "
    "interruption."
)
RECIPE_EXIT_CODES = (
    "Declare distinct exit-code constants and return them by intent: "
    "`EXIT_OK = 0`, `EXIT_USER_ERROR = 2`, `EXIT_INTERNAL_ERROR = 3`. "
    "A script that uses only 0 and 1 is below the contract — non-zero "
    "must be subdivided when the caller's recovery action differs."
)

_FILE_WRITE_RE = re.compile(
    r"\.write_text\s*\(|\.write_bytes\s*\(|\bopen\s*\([^)]*[\"']w"
)
_OS_REPLACE_RE = re.compile(r"os\.replace\s*\(|\.replace\s*\(\s*[a-zA-Z_]")
_TMP_SUFFIX_RE = re.compile(r"['\"]\.tmp['\"]|with_suffix\s*\([^)]*tmp")


def _has_stdin_json(tree: ast.Module, source: str) -> bool:
    """True if the script reads stdin and parses JSON from it."""
    has_stdin_read = False
    has_json_loads = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "read":
            value = node.value
            if (
                isinstance(value, ast.Attribute)
                and value.attr == "stdin"
                and isinstance(value.value, ast.Name)
                and value.value.id == "sys"
            ):
                has_stdin_read = True
        if isinstance(node, ast.Attribute) and node.attr in ("loads", "load"):
            value = node.value
            if isinstance(value, ast.Name) and value.id == "json":
                has_json_loads = True
    if has_stdin_read and has_json_loads:
        return True
    # Allow the shorter form `json.load(sys.stdin)` even without an explicit
    # `.read()` call.
    return bool(re.search(r"json\.load\s*\(\s*sys\.stdin", source))


def _has_atomic_write(source: str) -> bool:
    if not _FILE_WRITE_RE.search(source):
        # No file writes detected — rule is inapplicable, treat as pass.
        return True
    return bool(_OS_REPLACE_RE.search(source) and _TMP_SUFFIX_RE.search(source))


def _has_distinct_error_codes(tree: ast.Module) -> bool:
    """True if at least 2 distinct non-zero exit-code constants are declared."""
    distinct_nonzero: set[int] = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = getattr(node, "value", None)
            if isinstance(value, ast.Constant) and isinstance(value.value, int):
                if value.value > 0:
                    distinct_nonzero.add(value.value)
    return len(distinct_nonzero) >= 2


def _scan_file(path: Path) -> dict[str, list[dict]]:
    findings_by_rule: dict[str, list[dict]] = {
        RULE_STDIN_JSON: [],
        RULE_ATOMIC_WRITE: [],
        RULE_EXIT_CODES: [],
    }
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as err:
        print(f"error: cannot read {path}: {err}", file=sys.stderr)
        return findings_by_rule
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as err:
        findings_by_rule[RULE_STDIN_JSON].append(
            emit_json_finding(
                rule_id=RULE_STDIN_JSON,
                status="fail",
                location={"line": err.lineno or 0, "context": str(err.msg)},
                reasoning=f"Cannot parse {path}: {err}",
                recommended_changes="Fix the syntax error before auditing.",
            )
        )
        return findings_by_rule

    if not _has_stdin_json(tree, source):
        findings_by_rule[RULE_STDIN_JSON].append(
            emit_json_finding(
                rule_id=RULE_STDIN_JSON,
                status="fail",
                location=None,
                reasoning=(
                    "No `json.loads(sys.stdin.read())` (or equivalent) "
                    "found. The skill-helper contract requires the "
                    "payload to arrive on stdin as JSON."
                ),
                recommended_changes=RECIPE_STDIN_JSON,
            )
        )

    if not _has_atomic_write(source):
        findings_by_rule[RULE_ATOMIC_WRITE].append(
            emit_json_finding(
                rule_id=RULE_ATOMIC_WRITE,
                status="warn",
                location=None,
                reasoning=(
                    "File writes detected but no atomic-write pattern "
                    "(`.tmp` + `os.replace`) found. Direct writes can "
                    "leave half-written state on interruption."
                ),
                recommended_changes=RECIPE_ATOMIC_WRITE,
            )
        )

    if not _has_distinct_error_codes(tree):
        findings_by_rule[RULE_EXIT_CODES].append(
            emit_json_finding(
                rule_id=RULE_EXIT_CODES,
                status="warn",
                location=None,
                reasoning=(
                    "Fewer than two distinct non-zero exit-code "
                    "constants declared. The contract calls for "
                    "subdividing failure (e.g., user vs internal "
                    "error) when the caller's recovery action differs."
                ),
                recommended_changes=RECIPE_EXIT_CODES,
            )
        )

    return findings_by_rule


def _iter_targets(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.glob("*.py")))
        elif p.is_file():
            out.append(p)
        else:
            print(f"warning: {p} not found, skipping", file=sys.stderr)
    return out


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tier-1 skill-helper-profile checks for Python scripts.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Paths to Python files or directories.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    targets = _iter_targets(args.paths)
    if not targets:
        print("error: no Python files found", file=sys.stderr)
        return EXIT_USAGE

    accumulated: dict[str, list[dict]] = {
        RULE_STDIN_JSON: [],
        RULE_ATOMIC_WRITE: [],
        RULE_EXIT_CODES: [],
    }
    for path in targets:
        per_file = _scan_file(path)
        for rule_id, findings in per_file.items():
            accumulated[rule_id].extend(findings)

    envelopes = [
        emit_rule_envelope(rule_id, findings)
        for rule_id, findings in accumulated.items()
    ]
    print_envelope(envelopes)

    has_fail = any(env["overall_status"] == "fail" for env in envelopes)
    return EXIT_FAIL if has_fail else EXIT_CLEAN


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
