#!/usr/bin/env python3
"""Tier-1 README secrets scanner.

Scans README.md files for committed credentials:
  - Named API key patterns (AWS, GitHub, OpenAI, Anthropic, Stripe).
  - Credential-shaped assignments inside fenced code blocks
    (PASSWORD=, TOKEN=, SECRET=, API_KEY=...), with obvious
    placeholders (<FOO>, ${VAR}, your-..., example, etc.) skipped.
  - Internal/private URLs outside reserved example TLDs (matches
    `.corp.`, `.internal.`, `.prod.` host components).

All findings are FAIL. A FAIL excludes the file from Tier-2 judgment.

Example:
    ./check_secrets.py README.md path/to/docs/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_MD_EXTENSIONS = (".md", ".markdown")

_NAMED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub personal access token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub fine-grained PAT", re.compile(r"github_pat_[A-Za-z0-9_]{82}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{48}")),
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_-]{80,}")),
    ("Stripe live key", re.compile(r"sk_live_[A-Za-z0-9]{24}")),
]

_CREDENTIAL_VAR_RE = re.compile(
    r"\b(password|secret|token|api_key|access_key|private_key)"
    r"\s*=\s*(?P<q>[\"']?)(?P<value>[^\s\"']+)(?P=q)",
    re.IGNORECASE,
)

_INTERNAL_HOST_RE = re.compile(
    r"https?://[A-Za-z0-9.-]*\.(corp|internal|prod|prd|intranet)\.[A-Za-z]{2,}"
)

_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})\s*(?P<lang>\S*)")
_FRONTMATTER_FENCE = "---"

_PLACEHOLDER_VALUE_PREFIXES = (
    "$",
    "{",
    "<",
    "your-",
    "your_",
    "example",
    "redacted",
    "null",
    "none",
    "undefined",
    "placeholder",
    "todo",
    "fixme",
    "xxx",
    "changeme",
    "change-me",
    "change_me",
    "foo",
    "bar",
    "baz",
    "abc",
    "xyz",
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
            print(f"check_secrets.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _emit(path: Path, finding: str, lineno: int) -> None:
    print(f"FAIL  {path} — secret: {finding} at line {lineno}")
    print(
        "  Recommendation: Remove the value, rotate the credential if real, "
        "and replace with a clearly-marked placeholder (<YOUR_API_KEY>) "
        "plus an env-var reference in prose."
    )


def _strip_frontmatter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return lines
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_FENCE:
            return [""] * (idx + 1) + lines[idx + 1 :]
    return lines


def _is_placeholder(value: str) -> bool:
    return value.lower().startswith(_PLACEHOLDER_VALUE_PREFIXES)


def _scan_file(path: Path) -> bool:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_secrets.py: cannot read {path}: {err}", file=sys.stderr)
        return False
    lines = _strip_frontmatter(raw)
    any_fail = False
    in_fence = False
    fence_marker: str | None = None
    for lineno, line in enumerate(lines, 1):
        match = _FENCE_RE.match(line)
        if match and (not in_fence or line.startswith(fence_marker or "")):
            if not in_fence:
                in_fence = True
                fence_marker = match.group("fence")
            else:
                in_fence = False
                fence_marker = None
            continue
        for name, pattern in _NAMED_PATTERNS:
            if pattern.search(line):
                _emit(path, name, lineno)
                any_fail = True
        if in_fence:
            cred = _CREDENTIAL_VAR_RE.search(line)
            if cred and not _is_placeholder(cred.group("value")):
                _emit(path, "credential variable assignment", lineno)
                any_fail = True
        if _INTERNAL_HOST_RE.search(line):
            _emit(path, "internal hostname", lineno)
            any_fail = True
    return any_fail


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_secrets.py",
        description=(
            "Tier-1 README secrets scanner "
            "(named API keys + credential assignments + internal URLs)."
        ),
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
            if _scan_file(f):
                any_fail = True
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
