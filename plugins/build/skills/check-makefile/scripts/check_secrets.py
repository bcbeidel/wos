#!/usr/bin/env python3
"""Tier-1 Makefile secrets scanner — emits JSON envelope per `_common`.

Scans Makefile / GNUmakefile / *.mk for committed credentials:
  - Named API key patterns (AWS, GitHub, OpenAI, Anthropic, Stripe).
  - Credential-shaped variable assignments (TOKEN, SECRET, PASSWORD,
    API_KEY) with obvious placeholders ($VAR, {TEMPLATE}, "your-...")
    skipped.

Single-rule script. Emits one envelope: rule_id="secret".
All findings are status="fail". A FAIL excludes the file from Tier-2 judgment.

Exit codes: 0 on clean (overall_status="pass" / "inapplicable"),
1 on overall_status="fail", 64 on argument error.

Example:
    ./check_secrets.py path/to/Makefile path/to/mk/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
RULE_ID = "secret"

_NAMED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub personal access token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub fine-grained PAT", re.compile(r"github_pat_[A-Za-z0-9_]{82}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{48}")),
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_-]{80,}")),
    ("Stripe live key", re.compile(r"sk_live_[A-Za-z0-9]{24}")),
]

_CREDENTIAL_VAR_RE = re.compile(
    r"(password|secret|token|api_key|access_key|private_key)"
    r"\s*[:?+]?=\s*(?P<value>[^\s#]+)",
    re.IGNORECASE,
)

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
    '"',
    "'",
)

_RECIPE_SECRET = (
    "Remove the secret from the Makefile and rotate the credential "
    "(assume the value in source is already compromised). Replace with "
    "an `-include .env` at the top of the file (and ensure `.env` is "
    "gitignored). Commit a `.env.example` placeholder instead.\n\n"
    "Example:\n"
    "    -include .env          # .env gitignored; commit .env.example instead\n"
    "    API_TOKEN ?=                     # set in .env\n"
)


class _UsageError(Exception):
    pass


def _is_makefile(path: Path) -> bool:
    return path.name in ("Makefile", "GNUmakefile") or path.suffix == ".mk"


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_makefile(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_makefile(child):
                    files.append(child)
        else:
            print(f"check_secrets.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _is_placeholder(value: str) -> bool:
    lowered = value.lower().strip('"').strip("'")
    return lowered.startswith(_PLACEHOLDER_VALUE_PREFIXES) or not lowered


def _scan_file(path: Path) -> list[dict]:
    """Return list of finding dicts for one file."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_secrets.py: cannot read {path}: {err}", file=sys.stderr)
        return []
    findings: list[dict] = []
    for lineno, line in enumerate(lines, 1):
        for name, pattern in _NAMED_PATTERNS:
            if pattern.search(line):
                findings.append(
                    emit_json_finding(
                        rule_id=RULE_ID,
                        status="fail",
                        location={
                            "line": lineno,
                            "context": f"{path}: {name}",
                        },
                        reasoning=(
                            f"Detected {name} pattern at line {lineno}. "
                            "Committed credentials leak via git history, "
                            "CI logs, and shoulder-surfed terminals."
                        ),
                        recommended_changes=_RECIPE_SECRET,
                    )
                )
        match = _CREDENTIAL_VAR_RE.search(line)
        if match and not _is_placeholder(match.group("value")):
            findings.append(
                emit_json_finding(
                    rule_id=RULE_ID,
                    status="fail",
                    location={
                        "line": lineno,
                        "context": f"{path}: credential variable assignment",
                    },
                    reasoning=(
                        f"Credential-shaped variable assignment at line {lineno} "
                        "with a non-placeholder literal value. Assume the value "
                        "is compromised and rotate it."
                    ),
                    recommended_changes=_RECIPE_SECRET,
                )
            )
    return findings


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_secrets.py",
        description=(
            "Tier-1 Makefile secrets scanner (named API keys + credential assignments)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more Makefile / *.mk files or directories (non-recursive).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        files = _collect_targets(args.paths)
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130

    all_findings: list[dict] = []
    for f in files:
        all_findings.extend(_scan_file(f))

    envelope = emit_rule_envelope(rule_id=RULE_ID, findings=all_findings)
    print_envelope(envelope)
    return 1 if envelope["overall_status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
