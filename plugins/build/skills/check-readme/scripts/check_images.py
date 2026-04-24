#!/usr/bin/env python3
"""Tier-1 README image checker.

Three orthogonal sub-checks against inline images:
  - alt-text (WARN): every image has non-empty, non-placeholder alt
    text. Placeholder alts rejected: image, img, logo, badge, icon,
    or the filename itself.
  - image-size (WARN): local image files ≤ 500 KB each; total local
    image bytes ≤ 2 MB. HTTP image sizes are not inspected.
  - badge-overload (WARN): ≤ 5 badge-shaped images in the prelude
    (between H1 and the first non-image block). Badge detection:
    alt text or URL mentions `badge`, `shield`, or host matches
    `shields.io` / `img.shields.io` / `badge.fury.io`.

Example:
    ./check_images.py README.md path/to/docs/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

EXIT_USAGE = 64

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

MAX_IMAGE_BYTES = 500 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_BADGES = 5

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+")
_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")

_PLACEHOLDER_ALTS = {
    "image",
    "img",
    "logo",
    "badge",
    "icon",
    "screenshot",
    "picture",
    "photo",
}

_BADGE_HOSTS = (
    "shields.io",
    "img.shields.io",
    "badge.fury.io",
    "badgen.net",
    "codecov.io",
    "travis-ci.org",
    "travis-ci.com",
    "circleci.com",
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
            print(f"check_images.py: path not found: {target}", file=sys.stderr)
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


def _is_placeholder_alt(alt: str, url: str) -> bool:
    stripped = alt.strip().lower()
    if not stripped:
        return True
    if stripped in _PLACEHOLDER_ALTS:
        return True
    filename = Path(urlparse(url).path).name.lower()
    if stripped == filename:
        return True
    name_only = Path(filename).stem
    return bool(name_only) and stripped == name_only


def _is_badge(alt: str, url: str) -> bool:
    hay = f"{alt} {url}".lower()
    if "badge" in hay or "shield" in hay:
        return True
    host = urlparse(url).hostname or ""
    return any(host.endswith(h) for h in _BADGE_HOSTS)


def _local_image_size(path: Path, url: str) -> int | None:
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        return None
    target = (path.parent / unquote(parsed.path)).resolve()
    if not target.exists() or not target.is_file():
        return None
    try:
        return target.stat().st_size
    except OSError:
        return None


def _parse_blocks_until_first_non_image(
    lines: list[str], start: int
) -> tuple[int, int]:
    """Count badge-shaped images in the prelude between the H1 line and the
    first non-image, non-blank, non-fence-delimited content block."""
    badge_count = 0
    for idx in range(start, len(lines)):
        line = lines[idx].strip()
        if not line:
            continue
        if _FENCE_RE.match(line):
            break
        if _HEADING_RE.match(line):
            break
        matches = list(_IMAGE_RE.finditer(line))
        if not matches:
            text_without_images = _IMAGE_RE.sub("", line).strip()
            if text_without_images and not all(
                tok.startswith("[") and tok.endswith(")")
                for tok in text_without_images.split()
            ):
                break
        for m in matches:
            if _is_badge(m.group(1), m.group(2)):
                badge_count += 1
    return badge_count, start


def _find_h1_lineno(lines: list[str]) -> int | None:
    for idx, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("## "):
            return idx
    return None


def _check_file(path: Path) -> None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_images.py: cannot read {path}: {err}", file=sys.stderr)
        return
    lines = _strip_frontmatter(raw)

    total_bytes = 0
    size_warn_emitted = False
    alt_warn_emitted = False
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
        for m in _IMAGE_RE.finditer(line):
            alt, url = m.group(1), m.group(2)
            if not alt_warn_emitted and _is_placeholder_alt(alt, url):
                _emit(
                    "WARN",
                    path,
                    "alt-text",
                    f"line {lineno}: image `{url}` has empty or placeholder "
                    f"alt text ({alt!r})",
                    "Describe what the image conveys — screen readers and "
                    "failing-image fallbacks depend on it",
                )
                alt_warn_emitted = True
            size = _local_image_size(path, url)
            if size is not None:
                total_bytes += size
                if size > MAX_IMAGE_BYTES and not size_warn_emitted:
                    _emit(
                        "WARN",
                        path,
                        "image-size",
                        f"line {lineno}: local image `{url}` is "
                        f"{size // 1024} KB (> {MAX_IMAGE_BYTES // 1024} KB)",
                        "Convert to SVG or asciicast, recompress as WebP, or "
                        "move the asset off-repo",
                    )
                    size_warn_emitted = True

    if total_bytes > MAX_TOTAL_BYTES and not size_warn_emitted:
        _emit(
            "WARN",
            path,
            "image-size",
            f"total local image bytes {total_bytes // 1024} KB "
            f"(> {MAX_TOTAL_BYTES // 1024} KB)",
            "Trim oversized assets or move them off-repo",
        )

    h1_idx = _find_h1_lineno(lines)
    if h1_idx is not None:
        badge_count, _ = _parse_blocks_until_first_non_image(lines, h1_idx + 1)
        if badge_count > MAX_BADGES:
            _emit(
                "WARN",
                path,
                "badge-overload",
                f"{badge_count} badges in the prelude (> {MAX_BADGES})",
                "Trim to the badges a reader would actually check: CI, "
                "version, license, coverage",
            )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_images.py",
        description="Tier-1 README image checker (alt text, size, badges).",
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
        files = _collect_targets(args.paths)
        for f in files:
            _check_file(f)
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
