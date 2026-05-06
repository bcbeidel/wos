#!/usr/bin/env python3
"""Tier-1 README structural checker.

Emits a JSON ARRAY of seven envelopes per `_common.py`:

  - h1-present (FAIL): exactly one H1 on the first non-frontmatter
    content line.
  - heading-hierarchy (WARN): no skipped heading levels (MD001).
  - section-coverage (WARN): Installation, Usage (or Quickstart),
    and License H2 sections present.
  - section-order (WARN): canonical H2 sequence respected when
    sections are present.
  - toc-threshold (WARN): TOC heading present when document exceeds
    400 rendered lines.
  - size (WARN): document length <= 500 non-blank lines.
  - prose-line-length (WARN): source lines <= 120 characters,
    excluding fenced code blocks, tables, and bare-URL lines.

Exit codes:
  0  — all envelopes pass / warn / inapplicable
  1  — any envelope overall_status=fail
  64 — usage error

Example:
    ./check_structure.py README.md path/to/docs/
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

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

MAX_PROSE_LINE = 120
SIZE_WARN_LINES = 500
TOC_THRESHOLD_LINES = 400

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")
_BARE_URL_RE = re.compile(r"^\s*https?://\S+\s*$")

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

_RULE_ORDER: list[str] = [
    "h1-present",
    "heading-hierarchy",
    "section-coverage",
    "section-order",
    "toc-threshold",
    "size",
    "prose-line-length",
]

_RECIPE_H1_PRESENT = (
    "Ensure exactly one `# Title` line as the first non-frontmatter content "
    "of the file; demote or remove any other H1.\n\n"
    "Example:\n"
    "    ## Project\n"
    "    This is a thing.\n"
    "    # My Project\n"
    "      -> # My Project\n"
    "         This is a thing.\n"
)

_RECIPE_HEADING_HIERARCHY = (
    "Promote the skipped heading to match the sequence, or insert the "
    "missing intermediate level. Accessibility tools and auto-TOCs rely "
    "on sequential heading levels.\n\n"
    "Example:\n"
    "    ## Installation\n"
    "    #### Linux\n"
    "      -> ## Installation\n"
    "         ### Linux\n"
)

_RECIPE_SECTION_COVERAGE = (
    "Add the missing H2 section (Installation, Usage, or License) in "
    "reader-intent order. These three are the minimum sections a project "
    "README owes its readers.\n\n"
    "Example:\n"
    "    (no License section)\n"
    "      -> ## License\n"
    "         MIT — see [LICENSE](LICENSE).\n"
)

_RECIPE_SECTION_ORDER = (
    "Reorder H2 sections to match the path readers actually take through "
    "the document: Prerequisites -> Installation -> Usage -> "
    "Configuration -> Troubleshooting -> Contributing -> License.\n\n"
    "Example:\n"
    "    ## License (before ## Installation)\n"
    "      -> Move License last; keep Installation early.\n"
)

_RECIPE_TOC_THRESHOLD = (
    "Add a hand-maintained Table of Contents under the opening paragraph. "
    "Long READMEs on npm / PyPI / fork views have no auto-TOC sidebar; a "
    "hand TOC is the only navigation.\n\n"
    "Example:\n"
    "    ## Table of Contents\n"
    "    - [Prerequisites](#prerequisites)\n"
    "    - [Installation](#installation)\n"
    "    - [Usage](#usage)\n"
)

_RECIPE_SIZE = (
    "Move detailed sections into `/docs/` and link in. Keep the README as "
    "an orientation layer — the README orients a stranger; docs explain "
    "the domain. Two roles, two files.\n\n"
    "Example:\n"
    "    800-line README with full API reference inline\n"
    "      -> README links to `docs/api.md`; deep content moves out.\n"
)

_RECIPE_PROSE_LINE_LENGTH = (
    "Hard-wrap prose to 120 columns; do not touch fenced code blocks, "
    "tables, or bare-URL lines. Reviewers read diffs, not rendered HTML; "
    "long lines produce bad diffs.\n"
)

_RECIPES: dict[str, str] = {
    "h1-present": _RECIPE_H1_PRESENT,
    "heading-hierarchy": _RECIPE_HEADING_HIERARCHY,
    "section-coverage": _RECIPE_SECTION_COVERAGE,
    "section-order": _RECIPE_SECTION_ORDER,
    "toc-threshold": _RECIPE_TOC_THRESHOLD,
    "size": _RECIPE_SIZE,
    "prose-line-length": _RECIPE_PROSE_LINE_LENGTH,
}


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


def _check_h1(
    path: Path,
    stripped: list[str],
    offset: int,
    headings: list[tuple[int, int, str]],
    per_rule: dict[str, list[dict]],
) -> None:
    first = _first_content_lineno(stripped)
    if first is None:
        per_rule["h1-present"].append(
            _make_finding(
                "h1-present",
                "fail",
                f"{path}: no content after frontmatter",
                f"{path} has no content after frontmatter; cannot have an H1.",
                line=offset + 1,
            )
        )
        return
    first_line = stripped[first]
    is_h1 = first_line.startswith("# ") and not first_line.startswith("## ")
    h1_count = sum(1 for _, level, _ in headings if level == 1)
    if not is_h1:
        per_rule["h1-present"].append(
            _make_finding(
                "h1-present",
                "fail",
                f"{path}: first content line is not an H1",
                f"First content line at {first + offset + 1} of {path} is "
                "not an H1. README must open with a single `# <project>` "
                "title to anchor the document for readers and tooling.",
                line=first + offset + 1,
            )
        )
        return
    if h1_count != 1:
        per_rule["h1-present"].append(
            _make_finding(
                "h1-present",
                "fail",
                f"{path}: {h1_count} H1 headings found",
                f"Found {h1_count} H1 headings in {path}; expected exactly 1. "
                "Multiple H1s break document outlining and TOC tooling.",
                line=first + offset + 1,
            )
        )


def _check_hierarchy(
    path: Path,
    headings: list[tuple[int, int, str]],
    per_rule: dict[str, list[dict]],
) -> None:
    prev_level = 0
    for lineno, level, text in headings:
        if prev_level and level > prev_level + 1:
            per_rule["heading-hierarchy"].append(
                _make_finding(
                    "heading-hierarchy",
                    "warn",
                    f"{path}: line {lineno} jumps H{prev_level} -> H{level}",
                    f"Heading at line {lineno} of {path} jumps from "
                    f"H{prev_level} to H{level} ({text!r}). Heading levels "
                    "must be sequential (MD001).",
                    line=lineno,
                )
            )
            return
        prev_level = level


def _check_sections(
    path: Path,
    headings: list[tuple[int, int, str]],
    per_rule: dict[str, list[dict]],
) -> None:
    h2s = [(lineno, text) for lineno, level, text in headings if level == 2]
    seen: dict[str, int] = {}
    for lineno, text in h2s:
        canonical = _classify_section(text)
        if canonical and canonical not in seen:
            seen[canonical] = lineno
    missing = sorted(_REQUIRED_SECTIONS - set(seen))
    if missing:
        per_rule["section-coverage"].append(
            _make_finding(
                "section-coverage",
                "warn",
                f"{path}: missing required H2 section(s): {', '.join(missing)}",
                f"{path} is missing required H2 section(s): "
                f"{', '.join(missing)}. Installation, Usage, and License "
                "are the minimum sections a README owes its readers.",
                line=0,
            )
        )
    order = [name for name, _ in _CANONICAL_SECTIONS]
    observed = sorted(seen.keys(), key=lambda n: seen[n])
    expected = [n for n in order if n in seen]
    if observed != expected:
        per_rule["section-order"].append(
            _make_finding(
                "section-order",
                "warn",
                f"{path}: H2 sequence differs from canonical order",
                f"In {path}, H2 sequence {observed!r} does not match "
                f"canonical order {expected!r}. The order matches the path "
                "readers actually take through the document.",
                line=0,
            )
        )


def _check_toc_and_size(
    path: Path,
    lines: list[str],
    headings: list[tuple[int, int, str]],
    per_rule: dict[str, list[dict]],
) -> None:
    nonblank = sum(1 for ln in lines if ln.strip())
    rendered_lines = len(lines)
    has_toc = any(
        level == 2 and _TOC_HEADING_RE.match(text.strip())
        for _, level, text in headings
    )
    if rendered_lines > TOC_THRESHOLD_LINES and not has_toc:
        per_rule["toc-threshold"].append(
            _make_finding(
                "toc-threshold",
                "warn",
                f"{path}: {rendered_lines}-line document with no TOC",
                f"{path} is {rendered_lines} lines (> {TOC_THRESHOLD_LINES}) "
                "with no Table of Contents. Long READMEs on npm/PyPI/fork "
                "views have no auto-TOC sidebar.",
                line=0,
            )
        )
    if nonblank > SIZE_WARN_LINES:
        per_rule["size"].append(
            _make_finding(
                "size",
                "warn",
                f"{path}: {nonblank} non-blank lines",
                f"{path} is {nonblank} non-blank lines (> {SIZE_WARN_LINES}). "
                "Move detailed material into `/docs/` and link from the README.",
                line=0,
            )
        )


def _check_line_length(
    path: Path, lines: list[str], per_rule: dict[str, list[dict]]
) -> None:
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
            per_rule["prose-line-length"].append(
                _make_finding(
                    "prose-line-length",
                    "warn",
                    f"{path}: line {lineno} is {len(line)} chars",
                    f"Line {lineno} of {path} is {len(line)} chars (> "
                    f"{MAX_PROSE_LINE}). Long lines produce bad diffs.",
                    line=lineno,
                )
            )
            return


def _check_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_structure.py: cannot read {path}: {err}", file=sys.stderr)
        return
    stripped, offset = _strip_frontmatter(raw)
    headings = _parse_headings(stripped, offset)
    _check_h1(path, stripped, offset, headings, per_rule)
    _check_hierarchy(path, headings, per_rule)
    _check_sections(path, headings, per_rule)
    _check_toc_and_size(path, raw, headings, per_rule)
    _check_line_length(path, raw, per_rule)


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
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        files = _collect_targets(args.paths)
        for f in files:
            _check_file(f, per_rule)
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
