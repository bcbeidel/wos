#!/usr/bin/env python3
"""Tier-1 shellcheck wrapper for `run:` blocks in workflows.

Emits a JSON ARRAY with a single envelope (rule_id="shellcheck-run", WARN).

Extracts bash-effective `run:` block bodies, writes each to a temp file,
and pipes through `shellcheck`. Findings are reported as WARN. When
`shellcheck` is absent, emits a single inapplicable envelope and exits 0.

Exit codes:
  0   — overall_status pass / warn / inapplicable
  1   — overall_status fail (not produced — output is WARN)
  64  — usage error

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

_WORKFLOW_SUFFIXES = (".yml", ".yaml")
_FOCUS_CODES = {"SC2086", "SC2046", "SC2068", "SC2154"}

_RUN_HEADER_RE = re.compile(r"^(?P<indent>\s*)(?:-\s+)?run:\s*[|>][+-]?\s*$")
_GCC_LINE_RE = re.compile(
    r".+?:(\d+):(\d+):\s*(\w+):\s*(.+?)\s*\[(SC\d+)\]"
)

_RULE_ORDER: list[str] = ["shellcheck-run"]

_RECIPE_SHELLCHECK_RUN = (
    "Apply the shellcheck recommendation to the `run:` block. Most "
    "common: quote variable expansions (SC2086 — `\"$var\"`), use "
    "`$(...)` over backticks (SC2006), forward arguments with `\"$@\"` "
    "(SC2068). See https://www.shellcheck.net/wiki/<code> for the "
    "specific rule. Unquoted variables in `run:` blocks are the largest "
    "class of shell bugs in CI; every shellcheck finding is a real issue.\n"
)

_RECIPES: dict[str, str] = {"shellcheck-run": _RECIPE_SHELLCHECK_RUN}


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
            print(f"check_shellcheck.py: path not found: {p}", file=sys.stderr)
            raise _UsageError
    return files


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _extract_run_blocks(lines: list[str]) -> list[tuple[int, str]]:
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
            body_lines.append(
                line[base_indent + 2 :]
                if len(line) > base_indent + 2
                else line.strip()
            )
            i += 1
        body = "\n".join(body_lines)
        first_nonblank = next((ln for ln in body_lines if ln.strip()), "")
        if first_nonblank.startswith("#!") and "bash" not in first_nonblank:
            continue
        results.append((start_lineno, body))
    return results


def _run_shellcheck(body: str) -> str:
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
        return result.stdout + result.stderr
    finally:
        tmp_path.unlink(missing_ok=True)


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
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"check_shellcheck.py: cannot read {path}: {exc}", file=sys.stderr)
        return

    for start_lineno, body in _extract_run_blocks(lines):
        output = _run_shellcheck(body)
        if not output.strip():
            continue
        for line in output.splitlines():
            match = _GCC_LINE_RE.match(line)
            if not match:
                continue
            body_line, _col, severity, message, code = match.groups()
            absolute_line = start_lineno + int(body_line) - 1
            focus_marker = " (focus)" if code in _FOCUS_CODES else ""
            per_rule["shellcheck-run"].append(
                _make_finding(
                    "shellcheck-run",
                    "warn",
                    f"{path}:{absolute_line}: {code}{focus_marker} {message}",
                    f"shellcheck {code} ({severity}) at line "
                    f"{absolute_line} of {path}: {message}.",
                    line=absolute_line,
                )
            )


def _emit_inapplicable_array() -> list[dict]:
    return [
        emit_rule_envelope(rule_id=r, findings=[], inapplicable=True)
        for r in _RULE_ORDER
    ]


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_shellcheck.py",
        description="Shellcheck wrapper for GitHub Actions run: blocks.",
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
    if shutil.which("shellcheck") is None:
        print_envelope(_emit_inapplicable_array())
        print(
            "INFO: shellcheck not installed — install via "
            "`brew install shellcheck` (macOS) or the distribution "
            "package manager.",
            file=sys.stderr,
        )
        return 0
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
