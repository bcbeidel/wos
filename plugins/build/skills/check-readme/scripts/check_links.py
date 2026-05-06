#!/usr/bin/env python3
"""Tier-1 README link checker.

Emits a JSON ARRAY of three envelopes per `_common.py`:

  - broken-relative (FAIL): every relative link resolves to an
    existing file on disk.
  - broken-anchor (WARN): every fragment link (`#section`) matches
    an existing heading slug in the target file.
  - broken-external (WARN): when `lychee` or `markdown-link-check`
    is on PATH, external URLs return 2xx/3xx. External URL
    verification is skipped if neither tool is available (no
    finding emitted).

Heading slug generation uses GitHub's rule: lowercase, drop
punctuation that is not `-` or `_`, collapse whitespace to `-`.

Exit codes:
  0  — all envelopes pass / warn / inapplicable
  1  — any envelope overall_status=fail
  64 — usage error

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

_SLUG_STRIP_RE = re.compile(r"[^\w\s-]")
_SLUG_WHITESPACE_RE = re.compile(r"\s+")

_RULE_ORDER: list[str] = ["broken-relative", "broken-anchor", "broken-external"]

_RECIPE_BROKEN_RELATIVE = (
    "Create the target file, correct the path, or remove the link. Broken "
    "links erode trust and signal neglect — readers infer the rest of the "
    "doc is equally stale.\n\n"
    "Example:\n"
    "    [contributing](CONTRIBUTING.md)  (no such file)\n"
    "      -> add CONTRIBUTING.md, or drop the link from the README.\n"
)

_RECIPE_BROKEN_ANCHOR = (
    "Update the fragment to match the target heading's rendered slug. "
    "Anchor slugs are derived from heading text; drift between them "
    "silently breaks navigation.\n\n"
    "Example:\n"
    "    [see below](#setup-steps)  when heading is `## Setup`\n"
    "      -> [see below](#setup)\n"
)

_RECIPE_BROKEN_EXTERNAL = (
    "Update the URL, swap to a canonical source, or remove if the resource "
    "is gone. External URL rot is common; stale links point readers at "
    "error pages and undermine trust in the rest of the doc.\n"
)

_RECIPES: dict[str, str] = {
    "broken-relative": _RECIPE_BROKEN_RELATIVE,
    "broken-anchor": _RECIPE_BROKEN_ANCHOR,
    "broken-external": _RECIPE_BROKEN_EXTERNAL,
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
            print(f"check_links.py: path not found: {target}", file=sys.stderr)
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


def _extract_headings_from_path(target: Path) -> set[str]:
    try:
        raw = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return set()
    return _extract_headings(_strip_frontmatter(raw))


def _check_relative(
    path: Path,
    lineno: int,
    url: str,
    heading_cache: dict[Path, set[str]],
    per_rule: dict[str, list[dict]],
) -> None:
    if url.startswith("#"):
        anchor = _slugify(unquote(url[1:]))
        if not anchor:
            return
        slugs = heading_cache.setdefault(path, _extract_headings_from_path(path))
        if anchor not in slugs:
            per_rule["broken-anchor"].append(
                _make_finding(
                    "broken-anchor",
                    "warn",
                    f"{path}: line {lineno}: fragment `#{url[1:]}` not found",
                    f"Line {lineno} of {path} links to fragment `#{url[1:]}` "
                    "but no heading in the file slugifies to that anchor.",
                    line=lineno,
                )
            )
        return

    parsed = urlparse(url)
    if parsed.scheme:
        return

    url_path, _, fragment = url.partition("#")
    target_path = (path.parent / unquote(url_path)).resolve()
    if not target_path.exists():
        per_rule["broken-relative"].append(
            _make_finding(
                "broken-relative",
                "fail",
                f"{path}: line {lineno}: relative link `{url}` missing",
                f"Line {lineno} of {path} contains relative link `{url}` "
                f"which resolves to {target_path}, but no such file exists.",
                line=lineno,
            )
        )
        return
    if fragment and target_path.suffix.lower() in _MD_EXTENSIONS:
        slugs = heading_cache.setdefault(
            target_path, _extract_headings_from_path(target_path)
        )
        anchor = _slugify(unquote(fragment))
        if anchor and anchor not in slugs:
            per_rule["broken-anchor"].append(
                _make_finding(
                    "broken-anchor",
                    "warn",
                    f"{path}: line {lineno}: fragment `#{fragment}` missing in target",
                    f"Line {lineno} of {path} links to `{url}` but the "
                    f"fragment `#{fragment}` does not match any heading "
                    f"slug in {target_path}.",
                    line=lineno,
                )
            )


def _run_external_checker(path: Path, per_rule: dict[str, list[dict]]) -> None:
    tool = shutil.which("lychee") or shutil.which("markdown-link-check")
    if not tool:
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
    except (subprocess.TimeoutExpired, OSError):
        return
    if result.returncode != 0:
        summary = (result.stdout or result.stderr).strip().splitlines()
        tail = summary[-5:] if summary else ["(no output)"]
        per_rule["broken-external"].append(
            _make_finding(
                "broken-external",
                "warn",
                f"{path}: external link checker reported errors",
                f"{Path(tool).name} reported errors on {path}: "
                f"{' | '.join(tail)}",
                line=0,
            )
        )


def _check_file(
    path: Path,
    heading_cache: dict[Path, set[str]],
    per_rule: dict[str, list[dict]],
) -> None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_links.py: cannot read {path}: {err}", file=sys.stderr)
        return
    lines = _strip_frontmatter(raw)
    has_external = False
    for lineno, url in _extract_links(lines):
        if _is_external(url):
            has_external = True
            continue
        _check_relative(path, lineno, url, heading_cache, per_rule)
    if has_external:
        _run_external_checker(path, per_rule)


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
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        heading_cache: dict[Path, set[str]] = {}
        files = _collect_targets(args.paths)
        for f in files:
            _check_file(f, heading_cache, per_rule)
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
