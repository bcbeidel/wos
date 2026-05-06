#!/usr/bin/env python3
"""Tier-1 size checks for GitHub Actions workflows.

Emits a JSON ARRAY of two envelopes:

  - `run-block-size` (WARN): any `run:` block body exceeding ~20 non-blank
    lines (candidate for extraction to `.github/scripts/<name>.sh`).
  - `workflow-size` (WARN): whole-file length exceeding ~200 non-blank
    lines (candidate for splitting into reusable workflows / composite
    actions).

Exit codes:
  0   — overall_status pass / warn / inapplicable
  1   — overall_status fail (not produced — all findings are WARN)
  64  — usage error

Example:
    ./check_size.py .github/workflows/ci.yml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

_WORKFLOW_SUFFIXES = (".yml", ".yaml")
_RUN_BLOCK_LINE_LIMIT = 20
_WORKFLOW_LINE_LIMIT = 200

# Match `run: |`, `run: >`, `run: |-`, etc. with the leading indent captured.
_RUN_HEADER_RE = re.compile(r"^(?P<indent>\s*)(?:-\s+)?run:\s*[|>][+-]?\s*$")

_RULE_ORDER: list[str] = ["run-block-size", "workflow-size"]

_RECIPE_RUN_BLOCK_SIZE = (
    "Extract the `run:` body to `.github/scripts/<name>.sh` and replace "
    "with `bash .github/scripts/<name>.sh <args>`. Past ~20 lines, YAML "
    "is the wrong place for code — shellcheck cannot see inside the "
    "heredoc, tests cannot exercise it, and diff review is painful.\n\n"
    "Example:\n"
    "    - run: |\n"
    "        set -euo pipefail\n"
    "        # 40 lines of build logic\n"
    "      -> - run: bash .github/scripts/build.sh\n"
)

_RECIPE_WORKFLOW_SIZE = (
    "Extract one or more jobs to reusable workflows (`_<name>.yml` "
    "with `on: workflow_call:`) or step sequences to a composite "
    "action (`.github/actions/<name>/action.yml`). Call them from the "
    "original workflow. Past ~200 lines, every change risks touching "
    "unrelated work; the file becomes a maintenance tarpit.\n"
)

_RECIPES: dict[str, str] = {
    "run-block-size": _RECIPE_RUN_BLOCK_SIZE,
    "workflow-size": _RECIPE_WORKFLOW_SIZE,
}


class _UsageError(Exception):
    pass


def _iter_workflows(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            for suffix in _WORKFLOW_SUFFIXES:
                files.extend(sorted(p.glob(f"*{suffix}")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"check_size.py: path not found: {p}", file=sys.stderr)
            raise _UsageError
    return files


def _non_blank_count(lines: list[str]) -> int:
    return sum(1 for line in lines if line.strip())


def _scan_run_blocks(lines: list[str]) -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        header = _RUN_HEADER_RE.match(lines[i])
        if not header:
            i += 1
            continue
        start_lineno = i + 1
        base_indent = len(header.group("indent"))
        body: list[str] = []
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                body.append(line)
                i += 1
                continue
            stripped_indent = len(line) - len(line.lstrip(" "))
            if stripped_indent <= base_indent:
                break
            body.append(line)
            i += 1
        results.append((start_lineno, _non_blank_count(body)))
    return results


def _make_finding(
    rule_id: str,
    severity: str,
    location_context: str,
    reasoning: str,
    line: int = 0,
) -> dict:
    return emit_json_finding(
        rule_id=rule_id,
        status=severity,
        location={"line": line, "context": location_context},
        reasoning=reasoning,
        recommended_changes=_RECIPES[rule_id],
    )


def _scan(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"check_size.py: cannot read {path}: {exc}", file=sys.stderr)
        return

    lines = text.splitlines()
    file_nonblank = _non_blank_count(lines)

    if file_nonblank > _WORKFLOW_LINE_LIMIT:
        per_rule["workflow-size"].append(
            _make_finding(
                "workflow-size",
                "warn",
                f"{path}: {file_nonblank} non-blank lines "
                f"(> {_WORKFLOW_LINE_LIMIT})",
                f"{path} has {file_nonblank} non-blank lines, exceeding "
                f"the soft cap of {_WORKFLOW_LINE_LIMIT}. Past this size, "
                "every change risks touching unrelated jobs.",
                line=1,
            )
        )

    for start_lineno, block_len in _scan_run_blocks(lines):
        if block_len > _RUN_BLOCK_LINE_LIMIT:
            per_rule["run-block-size"].append(
                _make_finding(
                    "run-block-size",
                    "warn",
                    f"{path}:{start_lineno}: run block has "
                    f"{block_len} non-blank lines",
                    f"`run:` block at line {start_lineno} of {path} has "
                    f"{block_len} non-blank lines (> "
                    f"{_RUN_BLOCK_LINE_LIMIT}). YAML is the wrong place "
                    "for code at this size.",
                    line=start_lineno,
                )
            )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_size.py",
        description="Size checks for GitHub Actions workflows.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more workflow .yml/.yaml files or directories.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        files = _iter_workflows(args.paths)
        for path in files:
            _scan(path, per_rule)
        envelopes = [
            emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in _RULE_ORDER
        ]
        print_envelope(envelopes)
        any_fail = any(e["overall_status"] == "fail" for e in envelopes)
        return 1 if any_fail else 0
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
