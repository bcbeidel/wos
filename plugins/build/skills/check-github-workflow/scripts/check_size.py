#!/usr/bin/env python3
"""Tier-1 size checks for GitHub Actions workflows.

Two INFO findings:
  - `run-block-size`: any `run:` block body exceeding ~20 non-blank lines
    (candidate for extraction to `.github/scripts/<name>.sh`).
  - `workflow-size`: whole-file length exceeding ~200 non-blank lines
    (candidate for splitting into reusable workflows / composite actions).

Example:
    ./check_size.py .github/workflows/ci.yml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_WORKFLOW_SUFFIXES = (".yml", ".yaml")
_RUN_BLOCK_LINE_LIMIT = 20
_WORKFLOW_LINE_LIMIT = 200

# Match `run: |`, `run: >`, `run: |-`, etc. with the leading indent captured.
_RUN_HEADER_RE = re.compile(r"^(?P<indent>\s*)(?:-\s+)?run:\s*[|>][+-]?\s*$")


def _iter_workflows(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            for suffix in _WORKFLOW_SUFFIXES:
                files.extend(sorted(p.glob(f"*{suffix}")))
        elif p.is_file():
            files.append(p)
    return files


def _non_blank_count(lines: list[str]) -> int:
    return sum(1 for line in lines if line.strip())


def _scan_run_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Return list of (start_lineno, block_length) for each block-scalar run:.

    Block length is the number of non-blank lines in the block body.
    """
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
            # The block body is indented strictly deeper than the `run:` key.
            stripped_indent = len(line) - len(line.lstrip(" "))
            if stripped_indent <= base_indent:
                break
            body.append(line)
            i += 1
        results.append((start_lineno, _non_blank_count(body)))
    return results


def _scan(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"WARN     {path} — read: {exc}", file=sys.stderr)
        return findings

    lines = text.splitlines()
    file_nonblank = _non_blank_count(lines)

    if file_nonblank > _WORKFLOW_LINE_LIMIT:
        findings.append(
            f"INFO     {path} — workflow-size: {file_nonblank} non-blank lines "
            f"(> {_WORKFLOW_LINE_LIMIT})"
        )
        findings.append(
            "  Recommendation: Extract jobs to reusable workflows "
            "(`_<name>.yml` with `on: workflow_call:`) or step sequences to "
            "a composite action under `.github/actions/<name>/`."
        )

    for start_lineno, block_len in _scan_run_blocks(lines):
        if block_len > _RUN_BLOCK_LINE_LIMIT:
            findings.append(
                f"INFO     {path}:{start_lineno} — run-block-size: "
                f"{block_len} non-blank lines (> {_RUN_BLOCK_LINE_LIMIT})"
            )
            findings.append(
                "  Recommendation: Extract the body to "
                "`.github/scripts/<name>.sh` and invoke with "
                "`bash .github/scripts/<name>.sh`. Scaffold the script via "
                "`/build:build-bash-script` so it gets proper structure."
            )

    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Size checks for GitHub Actions workflows."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    workflows = _iter_workflows(args.paths)
    if not workflows:
        print("INFO     no workflow files found in provided paths")
        return 0

    for path in workflows:
        for line in _scan(path):
            print(line)

    return 0  # INFO-only; never FAIL.


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
