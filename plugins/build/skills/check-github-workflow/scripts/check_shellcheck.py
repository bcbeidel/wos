#!/usr/bin/env python3
"""Tier-1 shellcheck wrapper for `run:` blocks in workflows.

Extracts bash-effective `run:` block bodies, writes each to a temp
file, and pipes through `shellcheck`. Findings emitted as WARN. When
`shellcheck` is absent, emits a single INFO (`tool-missing`) per
invocation and exits 0 — matches the Missing Tools contract used by
other optional-tool wrappers.

Example:
    ./check_shellcheck.py .github/workflows/ci.yml
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXIT_USAGE = 64

_WORKFLOW_SUFFIXES = (".yml", ".yaml")
# SC codes we explicitly care about; others still show but are WARN-level advisory.
_FOCUS_CODES = {"SC2086", "SC2046", "SC2068", "SC2154"}

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


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _extract_run_blocks(lines: list[str]) -> list[tuple[int, str]]:
    """Return list of (start_lineno, body_text) for each block-scalar run:."""
    results: list[tuple[int, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        header = _RUN_HEADER_RE.match(lines[i])
        if not header:
            i += 1
            continue
        start_lineno = i + 1
        base_indent = len(header.group("indent"))
        body_lines: list[str] = []
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                body_lines.append("")
                i += 1
                continue
            if _indent_of(line) <= base_indent:
                break
            # Strip the leading indent so shellcheck sees a clean script.
            body_lines.append(
                line[base_indent + 2 :]
                if len(line) > base_indent + 2
                else line.strip()
            )
            i += 1
        body = "\n".join(body_lines)
        # Skip `#!/bin/sh` / PowerShell / python scripts — only bash-effective.
        first_nonblank = next((ln for ln in body_lines if ln.strip()), "")
        if first_nonblank.startswith("#!") and "bash" not in first_nonblank:
            continue
        results.append((start_lineno, body))
    return results


def _run_shellcheck(body: str) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tmp:
        tmp.write("#!/usr/bin/env bash\n")
        tmp.write(body)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    try:
        result = subprocess.run(
            ["shellcheck", "--format=gcc", "--shell=bash", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout + result.stderr
    finally:
        tmp_path.unlink(missing_ok=True)


def _scan(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"WARN     {path} — read: {exc}", file=sys.stderr)
        return findings

    for start_lineno, body in _extract_run_blocks(lines):
        _, output = _run_shellcheck(body)
        if not output.strip():
            continue
        for line in output.splitlines():
            # GCC format: <tmp>:<n>:<col>: <severity>: <message> [<SC####>]
            match = re.match(r".+?:(\d+):(\d+):\s*(\w+):\s*(.+?)\s*\[(SC\d+)\]", line)
            if not match:
                continue
            body_line, _col, severity, message, code = match.groups()
            absolute_line = start_lineno + int(body_line) - 1
            # Bump focused codes to a visible line; keep all as WARN.
            findings.append(
                f"WARN     {path}:{absolute_line} — shellcheck-run: "
                f"{code} ({severity}) {message}"
            )
            if code in _FOCUS_CODES:
                findings.append(
                    "  Recommendation: See https://www.shellcheck.net/wiki/"
                    f"{code}. Most common fix: quote variable expansions "
                    "(`\"$var\"`) or forward arguments with `\"$@\"`."
                )
            else:
                findings.append(
                    f"  Recommendation: See https://www.shellcheck.net/wiki/{code}."
                )

    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Shellcheck wrapper for GitHub Actions run: blocks."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    workflows = _iter_workflows(args.paths)
    if not workflows:
        print("INFO     no workflow files found in provided paths")
        return 0

    if shutil.which("shellcheck") is None:
        print(
            "INFO     tool-missing: shellcheck not installed — "
            "Tier-1 shell coverage reduced"
        )
        print("  Recommendation: Install via `brew install shellcheck` "
              "(macOS) or the distribution package manager.")
        return 0

    had_fail = False
    for path in workflows:
        for line in _scan(path):
            print(line)
            if line.startswith("FAIL"):
                had_fail = True

    return 1 if had_fail else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
