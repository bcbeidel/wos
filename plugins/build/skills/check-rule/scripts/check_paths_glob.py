#!/usr/bin/env python3
"""Tier-1 `paths:` glob validator for Claude Code rule files.

Emits a JSON envelope per `_common.py` for one rule:

- `paths-glob` (FAIL): each `paths:` entry is checked for empty pattern,
  unbalanced ``{...}``, unbalanced ``[...]``, and control characters.
  Supports inline lists (``paths: ["a", "b"]``) and block lists
  (``paths:\\n  - "a"\\n  - "b"``). Files without frontmatter or without
  a ``paths:`` key are skipped silently.

Exit codes:
  0  — overall_status pass / inapplicable
  1  — overall_status=fail
  64 — usage error

Example:
    ./check_paths_glob.py .claude/rules/
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
RULE_ID = "paths-glob"

CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
INLINE_RE = re.compile(r"^paths:\s*\[(?P<body>.*)\]\s*$")
BLOCK_HEADER_RE = re.compile(r"^paths:\s*$")
BLOCK_ITEM_RE = re.compile(r"^\s+-\s+(?P<value>.*\S)\s*$")

_RECIPE_PATHS_GLOB = (
    "Repair the malformed `paths:` glob so Claude Code can load the rule "
    "for the intended file set. Common subtypes:\n"
    "- Unclosed brace: close the `{...}` group\n"
    '    "src/api/**/*.{ts"   ->  "src/api/**/*.{ts,tsx}"\n'
    "- Unclosed bracket: close the `[...]` character class\n"
    '    "src/**/*.[ch"       ->  "src/**/*.[ch]"\n'
    "- Empty pattern: remove or replace with a real glob\n"
    "- Control character: re-type the pattern cleanly (no \\x00–\\x1F)\n\n"
    "A malformed glob silently fails to match — the rule never loads for "
    "any real file path."
)


def strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def split_top_level(body: str) -> list[str]:
    """Split a comma-separated inline list, respecting brace/bracket depth."""
    items: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(body):
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        elif ch == "," and depth == 0:
            items.append(body[start:i])
            start = i + 1
    items.append(body[start:])
    return [strip_quotes(item.strip()) for item in items]


def extract_paths_entries(lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_number, entry) tuples for every `paths:` glob."""
    if not lines or lines[0].rstrip("\n") != "---":
        return []

    end = next(
        (i for i in range(1, len(lines)) if lines[i].rstrip("\n") == "---"),
        None,
    )
    if end is None:
        return []

    entries: list[tuple[int, str]] = []
    in_block = False

    for idx in range(1, end):
        line = lines[idx].rstrip("\n")
        inline = INLINE_RE.match(line)
        if inline:
            in_block = False
            for item in split_top_level(inline["body"]):
                entries.append((idx + 1, item))
            continue
        if BLOCK_HEADER_RE.match(line):
            in_block = True
            continue
        if in_block:
            item = BLOCK_ITEM_RE.match(line)
            if item:
                entries.append((idx + 1, strip_quotes(item["value"].strip())))
                continue
            if line.strip() == "":
                continue
            in_block = False
    return entries


def _make_finding(path: Path, line_no: int, detail: str, reasoning: str) -> dict:
    return emit_json_finding(
        rule_id=RULE_ID,
        status="fail",
        location={"line": line_no, "context": f"{path}: {detail}"},
        reasoning=reasoning,
        recommended_changes=_RECIPE_PATHS_GLOB,
    )


def validate_entry(
    path: Path, line_no: int, entry: str, findings: list[dict]
) -> None:
    stripped = entry.strip()

    if not stripped:
        findings.append(
            _make_finding(
                path,
                line_no,
                "empty pattern",
                f"line {line_no}: empty `paths:` entry. An empty glob "
                "matches everything (or nothing, depending on parser), "
                "defeating path-scoping.",
            )
        )
        return

    if CONTROL_CHAR_RE.search(entry):
        findings.append(
            _make_finding(
                path,
                line_no,
                "control character in pattern",
                f"line {line_no}: control character in glob. Non-printable "
                "characters are never valid in file paths and cause silent "
                "matching failures.",
            )
        )

    if entry.count("{") != entry.count("}"):
        findings.append(
            _make_finding(
                path,
                line_no,
                f'unclosed brace in "{entry}"',
                f'line {line_no}: unbalanced `{{...}}` in "{entry}". '
                "Malformed braces cause the glob to silently fail to match; "
                "the rule never loads.",
            )
        )

    if entry.count("[") != entry.count("]"):
        findings.append(
            _make_finding(
                path,
                line_no,
                f'unclosed bracket in "{entry}"',
                f'line {line_no}: unbalanced `[...]` in "{entry}". '
                "Unmatched brackets are a parse error in minimatch-style "
                "globs; the rule fails to load.",
            )
        )


def scan_file(path: Path, findings: list[dict]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"warn: cannot read {path}: {err}", file=sys.stderr)
        return

    lines = text.splitlines(keepends=True)
    for line_no, entry in extract_paths_entries(lines):
        validate_entry(path, line_no, entry, findings)


def iter_targets(targets: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    for target in targets:
        if target.is_file():
            resolved.append(target)
        elif target.is_dir():
            resolved.extend(sorted(target.rglob("*.md")))
        else:
            print(f"error: path not found: {target}", file=sys.stderr)
            raise SystemExit(EXIT_USAGE)
    return resolved


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate paths: globs in Claude Code rule frontmatter.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Rule files or directories to scan (directories walked for *.md).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        files = iter_targets(args.paths)
        findings: list[dict] = []
        for file_path in files:
            scan_file(file_path, findings)
        envelope = emit_rule_envelope(rule_id=RULE_ID, findings=findings)
        print_envelope([envelope])
        return 1 if envelope["overall_status"] == "fail" else 0
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
