#!/usr/bin/env python3
"""Tier-1 README code-block checker.

Four orthogonal sub-checks across fenced code blocks:
  - fence-language (WARN): every fenced block carries a non-empty
    language info-string.
  - shell-prompt (WARN): no `$`, `>`, or `#` prompt prefix at the
    start of lines in shell-tagged blocks. The `#` prefix on a line
    that is wholly a bash comment (starts with `# ` and contains no
    shell syntax) is accepted.
  - smart-quotes (WARN): no smart quotes, em/en-dashes, or ellipsis
    inside fenced blocks.
  - code-line-length (WARN): fenced code lines ≤ 80 characters.

Example:
    ./check_codeblocks.py README.md path/to/docs/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

MAX_CODE_LINE = 80

_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})\s*(?P<lang>\S*)")
_SHELL_LANGS = {"bash", "sh", "shell", "console", "zsh", "pwsh", "ps1"}
_PROMPT_RE = re.compile(r"^\s*(\$|>|#)\s+\S")

_SMART_CHARS = {
    "‘": "U+2018 LEFT SINGLE QUOTATION MARK",
    "’": "U+2019 RIGHT SINGLE QUOTATION MARK",
    "“": "U+201C LEFT DOUBLE QUOTATION MARK",
    "”": "U+201D RIGHT DOUBLE QUOTATION MARK",
    "–": "U+2013 EN DASH",
    "—": "U+2014 EM DASH",
    "…": "U+2026 HORIZONTAL ELLIPSIS",
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
            print(f"check_codeblocks.py: path not found: {target}", file=sys.stderr)
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


def _is_bash_comment_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return False
    if stripped.startswith("#!"):
        return True
    rest = stripped[1:]
    return not rest or rest[0] == " "


def _check_file(path: Path) -> None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_codeblocks.py: cannot read {path}: {err}", file=sys.stderr)
        return
    lines = _strip_frontmatter(raw)

    emitted: set[tuple[str, int]] = set()
    in_fence = False
    fence_marker: str | None = None
    fence_lang: str = ""
    fence_start: int = 0

    for lineno, line in enumerate(lines, 1):
        match = _FENCE_RE.match(line)
        if match and (not in_fence or line.startswith(fence_marker or "")):
            if not in_fence:
                in_fence = True
                fence_marker = match.group("fence")
                fence_lang = match.group("lang").lower()
                fence_start = lineno
                if not fence_lang and ("fence-language", fence_start) not in emitted:
                    _emit(
                        "WARN",
                        path,
                        "fence-language",
                        f"fence at line {fence_start} has no language info-string",
                        "Add a language tag (bash, python, yaml, console, text)",
                    )
                    emitted.add(("fence-language", fence_start))
                continue
            in_fence = False
            fence_marker = None
            fence_lang = ""
            continue
        if not in_fence:
            continue

        if (
            fence_lang in _SHELL_LANGS
            and _PROMPT_RE.match(line)
            and not (fence_lang == "bash" and _is_bash_comment_line(line))
        ):
            key = ("shell-prompt", fence_start)
            if key not in emitted:
                _emit(
                    "WARN",
                    path,
                    "shell-prompt",
                    f"line {lineno} in {fence_lang} block starts with a "
                    "prompt prefix ($/>/#)",
                    "Strip prompt prefixes from command lines; show output "
                    "in a separate block",
                )
                emitted.add(key)

        for ch, desc in _SMART_CHARS.items():
            if ch in line:
                key = ("smart-quotes", fence_start)
                if key not in emitted:
                    _emit(
                        "WARN",
                        path,
                        "smart-quotes",
                        f"line {lineno} inside fenced block contains {desc}",
                        "Replace smart quotes and long dashes with ASCII "
                        "equivalents inside code blocks",
                    )
                    emitted.add(key)
                break

        if len(line) > MAX_CODE_LINE:
            key = ("code-line-length", fence_start)
            if key not in emitted:
                _emit(
                    "WARN",
                    path,
                    "code-line-length",
                    f"line {lineno} inside fenced block is {len(line)} "
                    f"chars (> {MAX_CODE_LINE})",
                    "Break long commands with `\\` continuations or pull "
                    "values into env vars",
                )
                emitted.add(key)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_codeblocks.py",
        description="Tier-1 README code-block checker (4 sub-checks).",
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
