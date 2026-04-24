#!/usr/bin/env python3
"""Tier-1 README link checker.

Three orthogonal sub-checks:
  - broken-relative (FAIL): every relative link resolves to an
    existing file on disk.
  - broken-anchor (WARN): every fragment link (`#section`) matches
    an existing heading slug in the target file.
  - broken-external (WARN): when `lychee` or `markdown-link-check`
    is on PATH, external URLs return 2xx/3xx. Emits `tool-missing`
    INFO and skips external URLs when neither tool is available.

Heading slug generation uses GitHub's rule: lowercase, drop
punctuation that is not `-` or `_`, collapse whitespace to `-`.

Example:
    ./check_links.py README.md path/to/docs/
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

EXIT_USAGE = 64

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

_SLUG_STRIP_RE = re.compile(r"[^\w\s-]")
_SLUG_WHITESPACE_RE = re.compile(r"\s+")


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
            print(f"check_links.py: path not found: {target}", file=sys.stderr)
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


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = _SLUG_STRIP_RE.sub("", text)
    text = _SLUG_WHITESPACE_RE.sub("-", text)
    return text


def _extract_headings(lines: list[str]) -> set[str]:
    slugs: set[str] = set()
    in_fence = False
    fence_marker: str | None = None
    for line in lines:
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
            slugs.add(_slugify(h.group(2)))
    return slugs


def _extract_links(
    lines: list[str],
) -> list[tuple[int, str]]:
    """Return (lineno, url) pairs for inline links outside fenced blocks."""
    found: list[tuple[int, str]] = []
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
        for m in _INLINE_LINK_RE.finditer(line):
            found.append((lineno, m.group(2)))
    return found


def _is_external(url: str) -> bool:
    return urlparse(url).scheme in ("http", "https", "mailto", "ftp")


def _check_relative(
    path: Path, lineno: int, url: str, heading_cache: dict[Path, set[str]]
) -> bool:
    if url.startswith("#"):
        anchor = _slugify(unquote(url[1:]))
        if not anchor:
            return False
        slugs = heading_cache.setdefault(path, _extract_headings_from_path(path))
        if anchor not in slugs:
            _emit(
                "WARN",
                path,
                "broken-anchor",
                f"line {lineno}: fragment `#{url[1:]}` has no matching heading slug",
                "Update the fragment to match the target heading's rendered slug",
            )
        return False

    parsed = urlparse(url)
    if parsed.scheme:
        return False

    url_path, _, fragment = url.partition("#")
    target_path = (path.parent / unquote(url_path)).resolve()
    if not target_path.exists():
        _emit(
            "FAIL",
            path,
            "broken-relative",
            f"line {lineno}: relative link `{url}` points to non-existent "
            f"file {target_path}",
            "Create the target file, correct the path, or drop the link",
        )
        return True
    if fragment and target_path.suffix.lower() in _MD_EXTENSIONS:
        slugs = heading_cache.setdefault(
            target_path, _extract_headings_from_path(target_path)
        )
        anchor = _slugify(unquote(fragment))
        if anchor and anchor not in slugs:
            _emit(
                "WARN",
                path,
                "broken-anchor",
                f"line {lineno}: fragment `#{fragment}` missing in {target_path}",
                "Update the fragment to match a heading slug in the target",
            )
    return False


def _extract_headings_from_path(target: Path) -> set[str]:
    try:
        raw = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return set()
    return _extract_headings(_strip_frontmatter(raw))


def _run_external_checker(path: Path) -> None:
    tool = shutil.which("lychee") or shutil.which("markdown-link-check")
    if not tool:
        print(
            f"INFO  {path} — tool-missing: no lychee/markdown-link-check on "
            "PATH — external URL verification skipped"
        )
        print(
            "  Recommendation: Install `lychee` (cargo install lychee) or "
            "`markdown-link-check` (npm i -g) to enable external link checks."
        )
        return
    cmd: list[str]
    if tool.endswith("lychee"):
        cmd = [tool, "--no-progress", "--offline=false", str(path)]
    else:
        cmd = [tool, "-q", str(path)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError) as err:
        print(f"INFO  {path} — tool-error: {Path(tool).name} failed: {err}")
        print("  Recommendation: Re-run when network is available or skip.")
        return
    if result.returncode != 0:
        summary = (result.stdout or result.stderr).strip().splitlines()
        tail = summary[-5:] if summary else ["(no output)"]
        _emit(
            "WARN",
            path,
            "broken-external",
            f"{Path(tool).name} reported errors: {' | '.join(tail)}",
            "Re-run the external checker to see per-URL results; update or "
            "remove broken URLs",
        )


def _check_file(path: Path, heading_cache: dict[Path, set[str]]) -> bool:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_links.py: cannot read {path}: {err}", file=sys.stderr)
        return False
    lines = _strip_frontmatter(raw)
    any_fail = False
    has_external = False
    for lineno, url in _extract_links(lines):
        if _is_external(url):
            has_external = True
            continue
        if _check_relative(path, lineno, url, heading_cache):
            any_fail = True
    if has_external:
        _run_external_checker(path)
    return any_fail


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_links.py",
        description="Tier-1 README link checker (relative + anchor + external).",
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
    heading_cache: dict[Path, set[str]] = {}
    try:
        files = _collect_targets(args.paths)
        for f in files:
            if _check_file(f, heading_cache):
                any_fail = True
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
