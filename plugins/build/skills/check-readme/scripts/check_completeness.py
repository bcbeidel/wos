#!/usr/bin/env python3
"""Tier-1 README completeness checker.

Five orthogonal sub-checks:
  - license-file (FAIL): a LICENSE file exists alongside the README
    (LICENSE, LICENSE.md, LICENSE.txt, COPYING).
  - license-link (WARN): the README has a heading matching
    /license/i and a link to the LICENSE file.
  - contributing-link (WARN): the README has a Contributing heading
    or a link to CONTRIBUTING.md.
  - todo-markers (WARN): no TODO / FIXME / XXX markers outside
    fenced code blocks.
  - readme-gitignored (WARN): the README path is not excluded by a
    `.gitignore` in the same directory or any parent up to $PWD.

Example:
    ./check_completeness.py README.md path/to/docs/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

_LICENSE_FILENAMES = (
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENSE.rst",
    "COPYING",
    "COPYING.md",
    "COPYING.txt",
)

_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LICENSE_HEADING_RE = re.compile(r"^licen[sc]e", re.IGNORECASE)
_CONTRIBUTING_HEADING_RE = re.compile(r"^contributing", re.IGNORECASE)
_LICENSE_LINK_RE = re.compile(
    r"\[[^\]]+\]\((?:\./)?(LICENSE|COPYING)[^)]*\)",
    re.IGNORECASE,
)
_CONTRIBUTING_LINK_RE = re.compile(
    r"\[[^\]]+\]\((?:\./)?CONTRIBUTING\.(md|rst|txt)[^)]*\)",
    re.IGNORECASE,
)
_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX)\b")


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
            print(f"check_completeness.py: path not found: {target}", file=sys.stderr)
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


def _strip_frontmatter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return lines
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_FENCE:
            return [""] * (idx + 1) + lines[idx + 1 :]
    return lines


def _has_license_file(readme: Path) -> bool:
    for name in _LICENSE_FILENAMES:
        if (readme.parent / name).exists():
            return True
    return False


def _parse_headings(lines: list[str]) -> list[str]:
    headings: list[str] = []
    in_fence = False
    fence_marker: str | None = None
    for line in lines:
        m = _FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence = True
                fence_marker = m.group("fence")
            elif line.startswith(fence_marker or ""):
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        h = _HEADING_RE.match(line)
        if h:
            headings.append(h.group(2).strip())
    return headings


def _check_license_link(path: Path, lines: list[str], body: str) -> None:
    headings = _parse_headings(lines)
    has_heading = any(_LICENSE_HEADING_RE.match(h) for h in headings)
    has_link = bool(_LICENSE_LINK_RE.search(body))
    if not has_heading or not has_link:
        parts: list[str] = []
        if not has_heading:
            parts.append("no `## License` heading")
        if not has_link:
            parts.append("no link to LICENSE file")
        _emit(
            "WARN",
            path,
            "license-link",
            "; ".join(parts),
            "Add a `## License` H2 with an SPDX identifier and a link to `LICENSE`",
        )


def _check_contributing_link(path: Path, lines: list[str], body: str) -> None:
    headings = _parse_headings(lines)
    has_heading = any(_CONTRIBUTING_HEADING_RE.match(h) for h in headings)
    has_link = bool(_CONTRIBUTING_LINK_RE.search(body))
    if not has_heading and not has_link:
        _emit(
            "WARN",
            path,
            "contributing-link",
            "no Contributing heading and no link to CONTRIBUTING.md",
            "Add a `## Contributing` H2 linking to `CONTRIBUTING.md`",
        )


def _check_todo_markers(path: Path, lines: list[str]) -> None:
    in_fence = False
    fence_marker: str | None = None
    for lineno, line in enumerate(lines, 1):
        m = _FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence = True
                fence_marker = m.group("fence")
            elif line.startswith(fence_marker or ""):
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        marker = _MARKER_RE.search(line)
        if marker:
            _emit(
                "WARN",
                path,
                "todo-markers",
                f"line {lineno}: `{marker.group(1)}` in published README",
                "Convert to a tracked issue and remove the marker from the README",
            )
            return


def _gitignore_patterns(dir_path: Path, stop_at: Path) -> list[tuple[Path, str]]:
    """Yield (dir, pattern) pairs from .gitignore files walking up from
    dir_path to stop_at (inclusive)."""
    patterns: list[tuple[Path, str]] = []
    current = dir_path.resolve()
    boundary = stop_at.resolve()
    while True:
        gi = current / ".gitignore"
        if gi.exists():
            try:
                for raw in gi.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    patterns.append((current, line))
            except OSError:
                pass
        if current == boundary:
            break
        if current.parent == current:
            break
        if boundary not in current.parents:
            break
        current = current.parent
    return patterns


def _check_readme_gitignored(path: Path) -> None:
    stop = Path.cwd().resolve()
    patterns = _gitignore_patterns(path.parent, stop)
    for base, pat in patterns:
        try:
            rel = path.resolve().relative_to(base)
        except ValueError:
            continue
        candidates = {path.name, str(rel), str(rel).lstrip("/")}
        stripped = pat.lstrip("/")
        if stripped in candidates or stripped == path.name:
            _emit(
                "WARN",
                path,
                "readme-gitignored",
                f"`{pat}` in {base / '.gitignore'} matches the README",
                "Remove the README entry from `.gitignore`; the README must "
                "be version-controlled",
            )
            return


def _check_file(path: Path) -> bool:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(
            f"check_completeness.py: cannot read {path}: {err}",
            file=sys.stderr,
        )
        return False
    lines = _strip_frontmatter(raw)
    body = "\n".join(lines)
    any_fail = False
    if not _has_license_file(path):
        _emit(
            "FAIL",
            path,
            "license-file",
            "no LICENSE / LICENSE.md / LICENSE.txt / COPYING next to README",
            "Add a LICENSE file with the full license text; see "
            "https://choosealicense.com",
        )
        any_fail = True
    _check_license_link(path, lines, body)
    _check_contributing_link(path, lines, body)
    _check_todo_markers(path, lines)
    _check_readme_gitignored(path)
    return any_fail


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_completeness.py",
        description="Tier-1 README completeness checker (5 sub-checks).",
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
