#!/usr/bin/env python3
"""Tier-1 README structural checker.

Seven orthogonal structural sub-checks against each target:
  - h1-present (FAIL): exactly one H1 on the first non-frontmatter
    content line.
  - heading-hierarchy (WARN): no skipped heading levels (MD001).
  - section-coverage (WARN): Installation, Usage (or Quickstart),
    and License H2 sections present.
  - section-order (WARN): canonical H2 sequence respected when
    sections are present.
  - toc-threshold (WARN): TOC heading present when document exceeds
    400 rendered lines.
  - size (WARN): document length ≤ 500 non-blank lines.
  - prose-line-length (WARN): source lines ≤ 120 characters,
    excluding fenced code blocks, tables, and bare-URL lines.

Example:
    ./check_structure.py README.md path/to/docs/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

MAX_PROSE_LINE = 120
SIZE_WARN_LINES = 500
TOC_THRESHOLD_LINES = 400

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")
_BARE_URL_RE = re.compile(r"^\s*https?://\S+\s*$")

# Canonical section order. Entries are tuples of (canonical name,
# regex-escaped patterns that match the heading text case-insensitively).
_CANONICAL_SECTIONS: list[tuple[str, re.Pattern[str]]] = [
    ("Prerequisites", re.compile(r"^(prerequisites|requirements)$", re.I)),
    ("Installation", re.compile(r"^(installation|install|setup)$", re.I)),
    (
        "Usage",
        re.compile(r"^(usage|quickstart|quick\s*start|getting\s*started)$", re.I),
    ),
    ("Configuration", re.compile(r"^(configuration|config)$", re.I)),
    ("Troubleshooting", re.compile(r"^(troubleshooting|faq)$", re.I)),
    ("Contributing", re.compile(r"^contributing$", re.I)),
    ("License", re.compile(r"^licen[sc]e$", re.I)),
]

_REQUIRED_SECTIONS = {"Installation", "Usage", "License"}

_TOC_HEADING_RE = re.compile(
    r"^(table\s+of\s+contents|contents|toc)$",
    re.I,
)


class _UsageError(Exception):
    pass


def _is_markdown(path: Path) -> bool:
    return path.suffix.lower() in _MD_EXTENSIONS


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_markdown(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_markdown(child):
                    files.append(child)
        else:
            print(f"check_structure.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _emit(
    severity: str,
    path: Path,
    check: str,
    message: str,
    recommendation: str,
) -> None:
    print(f"{severity}  {path} — {check}: {message}")
    print(f"  Recommendation: {recommendation}.")


def _strip_frontmatter(lines: list[str]) -> tuple[list[str], int]:
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return lines, 0
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_FENCE:
            return lines[idx + 1 :], idx + 1
    return lines, 0


def _first_content_lineno(lines: list[str]) -> int | None:
    for idx, line in enumerate(lines):
        if line.strip():
            return idx
    return None


def _parse_headings(lines: list[str], offset: int) -> list[tuple[int, int, str]]:
    """Return (lineno, level, text) triples. lineno is 1-indexed in the
    original (pre-strip) file."""
    headings: list[tuple[int, int, str]] = []
    in_fence = False
    fence_marker: str | None = None
    for idx, line in enumerate(lines):
        match = _FENCE_RE.match(line)
        if match:
            if not in_fence:
                in_fence = True
                fence_marker = match.group("fence")
            elif line.startswith(fence_marker or ""):
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        h = _HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            text = h.group(2).strip()
            headings.append((idx + offset + 1, level, text))
    return headings


def _classify_section(text: str) -> str | None:
    for name, pattern in _CANONICAL_SECTIONS:
        if pattern.match(text):
            return name
    return None


def _check_h1(path: Path, stripped: list[str], offset: int) -> bool:
    first = _first_content_lineno(stripped)
    if first is None:
        _emit(
            "FAIL",
            path,
            "h1-present",
            "file has no content after frontmatter",
            "Add `# <project-name>` as the first content line",
        )
        return True
    first_line = stripped[first]
    is_h1 = first_line.startswith("# ") and not first_line.startswith("## ")
    h1_count = sum(1 for _, level, _ in _parse_headings(stripped, offset) if level == 1)
    if not is_h1:
        _emit(
            "FAIL",
            path,
            "h1-present",
            f"first content line at {first + offset + 1} is not an H1",
            "Place a single `# <project-name>` H1 on the first content line "
            "(after any frontmatter)",
        )
        return True
    if h1_count != 1:
        _emit(
            "FAIL",
            path,
            "h1-present",
            f"{h1_count} H1 headings found, expected exactly 1",
            "Keep exactly one H1 (the project title); demote the others to H2",
        )
        return True
    return False


def _check_hierarchy(path: Path, headings: list[tuple[int, int, str]]) -> None:
    prev_level = 0
    for lineno, level, text in headings:
        if prev_level and level > prev_level + 1:
            _emit(
                "WARN",
                path,
                "heading-hierarchy",
                f"line {lineno}: heading level jumps from H{prev_level} to "
                f"H{level} ({text!r})",
                "Keep headings sequential (H1 → H2 → H3); insert the "
                "intermediate level or demote this heading",
            )
            return
        prev_level = level


def _check_sections(path: Path, headings: list[tuple[int, int, str]]) -> None:
    h2s = [(lineno, text) for lineno, level, text in headings if level == 2]
    seen: dict[str, int] = {}
    for lineno, text in h2s:
        canonical = _classify_section(text)
        if canonical and canonical not in seen:
            seen[canonical] = lineno
    missing = sorted(_REQUIRED_SECTIONS - set(seen))
    if missing:
        _emit(
            "WARN",
            path,
            "section-coverage",
            f"missing required H2 section(s): {', '.join(missing)}",
            "Add an H2 for each missing section in reader-intent order",
        )
    order = [name for name, _ in _CANONICAL_SECTIONS]
    observed = sorted(seen.keys(), key=lambda n: seen[n])
    expected = [n for n in order if n in seen]
    if observed != expected:
        _emit(
            "WARN",
            path,
            "section-order",
            f"H2 sequence {observed!r} does not match canonical order {expected!r}",
            "Reorder H2 sections: Prerequisites → Installation → Usage → "
            "Configuration → Troubleshooting → Contributing → License",
        )


def _check_toc_and_size(
    path: Path, lines: list[str], headings: list[tuple[int, int, str]]
) -> None:
    nonblank = sum(1 for ln in lines if ln.strip())
    rendered_lines = len(lines)
    has_toc = any(
        level == 2 and _TOC_HEADING_RE.match(text.strip())
        for _, level, text in headings
    )
    if rendered_lines > TOC_THRESHOLD_LINES and not has_toc:
        _emit(
            "WARN",
            path,
            "toc-threshold",
            f"document is {rendered_lines} lines (> {TOC_THRESHOLD_LINES}) "
            "with no Table of Contents",
            "Add a `## Table of Contents` with links to each H2",
        )
    if nonblank > SIZE_WARN_LINES:
        _emit(
            "WARN",
            path,
            "size",
            f"README is {nonblank} non-blank lines (> {SIZE_WARN_LINES})",
            "Move detailed material into `/docs/` and link from the README",
        )


def _check_line_length(path: Path, lines: list[str]) -> None:
    in_fence = False
    fence_marker: str | None = None
    for lineno, line in enumerate(lines, 1):
        match = _FENCE_RE.match(line)
        if match:
            if not in_fence:
                in_fence = True
                fence_marker = match.group("fence")
            elif line.startswith(fence_marker or ""):
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        if line.startswith("|"):
            continue
        if _BARE_URL_RE.match(line):
            continue
        if len(line) > MAX_PROSE_LINE:
            _emit(
                "WARN",
                path,
                "prose-line-length",
                f"line {lineno} is {len(line)} chars (> {MAX_PROSE_LINE})",
                f"Hard-wrap the prose to {MAX_PROSE_LINE} columns",
            )
            return


def _check_file(path: Path) -> bool:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_structure.py: cannot read {path}: {err}", file=sys.stderr)
        return False
    stripped, offset = _strip_frontmatter(raw)
    headings = _parse_headings(stripped, offset)
    any_fail = _check_h1(path, stripped, offset)
    _check_hierarchy(path, headings)
    _check_sections(path, headings)
    _check_toc_and_size(path, raw, headings)
    _check_line_length(path, raw)
    return any_fail


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_structure.py",
        description="Tier-1 README structural checker (7 sub-checks).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more .md files or directories (non-recursive).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    any_fail = False
    try:
        files = _collect_targets(args.paths)
        for f in files:
            if _check_file(f):
                any_fail = True
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
