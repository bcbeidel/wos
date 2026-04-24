#!/usr/bin/env python3
"""Deterministic Tier-1 checks for the RESOLVER.md managed region.

Six checks per target repo root:

- **markers-present** — both ``<!-- resolver:begin -->`` and
  ``<!-- resolver:end -->`` appear exactly once. FAIL otherwise.
- **filing-paths-resolve** — every Location column value in the filing
  table resolves to a directory on disk. FAIL on miss.
- **context-paths-resolve** — every doc path in the context table's
  "Load first" column resolves to a file on disk. FAIL on miss.
- **filing-rows-unique** — the filing table's first column (content
  type) has no duplicates. FAIL on duplicate.
- **context-rows-unique** — the context table's first column (task)
  has no duplicates. FAIL on duplicate.
- **mtime-stale** — RESOLVER.md mtime older than 90 days. WARN.

Paths containing template placeholders (``<...>``, ``*``) are skipped
by the resolver checks — they are documented templates, not concrete
paths.

Example:
    ./check_resolver.py .
    ./check_resolver.py /path/to/repo-a /path/to/repo-b
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

EXIT_USAGE = 2
EXIT_INTERRUPTED = 130

RESOLVER_FILENAME = "RESOLVER.md"
MARKER_BEGIN = "<!-- resolver:begin -->"
MARKER_END = "<!-- resolver:end -->"
STALE_SECONDS = 90 * 24 * 60 * 60

H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
SEPARATOR_ROW_RE = re.compile(r"^\s*\|[\s\-|:]+\|\s*$")
PLACEHOLDER_RE = re.compile(r"[<>*]")


def emit_fail(path: Path, check: str, detail: str, recommendation: str) -> None:
    print(f"FAIL  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def emit_warn(path: Path, check: str, detail: str, recommendation: str) -> None:
    print(f"WARN  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def extract_managed_region(text: str) -> str | None:
    begin_count = text.count(MARKER_BEGIN)
    end_count = text.count(MARKER_END)
    if begin_count != 1 or end_count != 1:
        return None
    start = text.index(MARKER_BEGIN) + len(MARKER_BEGIN)
    end = text.index(MARKER_END)
    if end <= start:
        return None
    return text[start:end]


def parse_table_cells(row_line: str) -> list[str]:
    match = TABLE_ROW_RE.match(row_line)
    if not match:
        return []
    inner = match.group(1)
    return [cell.strip() for cell in inner.split("|")]


def find_section_table(region: str, section_prefix: str) -> list[list[str]]:
    """Return data rows from the first markdown table inside the named H2 section.

    Matches H2 headings whose text starts with ``section_prefix`` (case-insensitive).
    Returns an empty list when the section or table is absent.
    """
    lines = region.splitlines()
    in_section = False
    table_started = False
    data_rows: list[list[str]] = []
    prefix_lower = section_prefix.lower()

    for line in lines:
        h2_match = H2_RE.match(line)
        if h2_match:
            heading = h2_match.group(1).strip().lower()
            if heading.startswith(prefix_lower):
                in_section = True
                table_started = False
                continue
            if in_section:
                break
            continue
        if not in_section:
            continue
        if TABLE_ROW_RE.match(line):
            if SEPARATOR_ROW_RE.match(line):
                table_started = True
                continue
            if not table_started:
                continue
            cells = parse_table_cells(line)
            if cells:
                data_rows.append(cells)
        elif table_started and not line.strip():
            break
    return data_rows


def strip_backticks(value: str) -> str:
    return value.strip().strip("`").strip()


def extract_paths_from_load_cell(cell: str) -> list[str]:
    """Parse one context-table "Load first" cell into a list of doc paths.

    Accepts three shapes:
      - single backticked path:        `foo/bar.md`
      - backticked comma-separated:    `foo.md`, `bar.md`
      - bracketed comma-separated:     [foo.md, bar.md]
    """
    inner = cell.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    parts = [strip_backticks(p) for p in inner.split(",")]
    return [p for p in parts if p]


def check_markers(resolver_path: Path, text: str) -> bool:
    begin_count = text.count(MARKER_BEGIN)
    end_count = text.count(MARKER_END)
    if begin_count == 1 and end_count == 1:
        return True
    emit_fail(
        resolver_path,
        "markers-present",
        f"expected exactly one {MARKER_BEGIN} and one {MARKER_END}; "
        f"found {begin_count} begin, {end_count} end",
        "Restore the managed-region markers and regenerate via "
        "/build:build-resolver --regenerate",
    )
    return False


def check_filing_table(resolver_path: Path, repo_root: Path, region: str) -> bool:
    rows = find_section_table(region, "Filing")
    ok = True
    seen_keys: dict[str, int] = {}
    for idx, cells in enumerate(rows, start=1):
        if len(cells) < 2:
            continue
        content_type = strip_backticks(cells[0])
        location = strip_backticks(cells[1])
        if not content_type or not location:
            continue
        if content_type in seen_keys:
            emit_fail(
                resolver_path,
                "filing-rows-unique",
                f"duplicate content-type '{content_type}' "
                f"(rows {seen_keys[content_type]} and {idx})",
                "Merge the duplicates into one row, or rename one content-type",
            )
            ok = False
        else:
            seen_keys[content_type] = idx
        if PLACEHOLDER_RE.search(location):
            continue
        resolved = (repo_root / location).resolve()
        if not resolved.is_dir():
            emit_fail(
                resolver_path,
                "filing-paths-resolve",
                f"filing location '{location}' "
                f"(content-type '{content_type}') does not resolve to a directory",
                "Create the directory, correct the path, or remove the row",
            )
            ok = False
    return ok


def check_context_table(resolver_path: Path, repo_root: Path, region: str) -> bool:
    rows = find_section_table(region, "Context")
    ok = True
    seen_tasks: dict[str, int] = {}
    for idx, cells in enumerate(rows, start=1):
        if len(cells) < 2:
            continue
        task = strip_backticks(cells[0])
        load_cell = cells[1]
        if not task or not load_cell.strip():
            continue
        if task in seen_tasks:
            emit_fail(
                resolver_path,
                "context-rows-unique",
                f"duplicate task '{task}' (rows {seen_tasks[task]} and {idx})",
                "Merge the duplicates into one row with a unioned doc list",
            )
            ok = False
        else:
            seen_tasks[task] = idx
        for doc_path in extract_paths_from_load_cell(load_cell):
            if PLACEHOLDER_RE.search(doc_path):
                continue
            resolved = (repo_root / doc_path).resolve()
            if not resolved.is_file():
                emit_fail(
                    resolver_path,
                    "context-paths-resolve",
                    f"context doc '{doc_path}' (task '{task}') "
                    "does not resolve to a file",
                    "Correct the path, or remove the entry from the bundle",
                )
                ok = False
    return ok


def check_mtime(resolver_path: Path) -> None:
    age_seconds = time.time() - resolver_path.stat().st_mtime
    if age_seconds > STALE_SECONDS:
        days = int(age_seconds / 86400)
        emit_warn(
            resolver_path,
            "mtime-stale",
            f"RESOLVER.md mtime is {days} days old (threshold 90)",
            "Run /build:build-resolver --regenerate to refresh "
            "against current disk state",
        )


def check_repo(repo_root: Path) -> bool:
    if not repo_root.is_dir():
        print(f"error: not a directory: {repo_root}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    resolver_path = repo_root / RESOLVER_FILENAME
    if not resolver_path.is_file():
        emit_fail(
            resolver_path,
            "markers-present",
            f"{RESOLVER_FILENAME} does not exist at repo root",
            "Create RESOLVER.md via /build:build-resolver",
        )
        return False
    try:
        text = resolver_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"error: cannot read {resolver_path}: {err}", file=sys.stderr)
        return False
    ok = True
    if not check_markers(resolver_path, text):
        check_mtime(resolver_path)
        return False
    region = extract_managed_region(text)
    if region is None:
        return False
    if not check_filing_table(resolver_path, repo_root, region):
        ok = False
    if not check_context_table(resolver_path, repo_root, region):
        ok = False
    check_mtime(resolver_path)
    return ok


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tier-1 deterministic checks for the RESOLVER.md managed region.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="One or more repo-root paths (defaults to current directory).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        all_ok = True
        for repo_root in args.paths:
            if not check_repo(repo_root):
                all_ok = False
        return 0 if all_ok else 1
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
