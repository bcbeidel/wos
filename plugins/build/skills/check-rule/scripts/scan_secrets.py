#!/usr/bin/env python3
"""Tier-1 secrets scanner for Claude Code rule files.

Emits a JSON envelope per `_common.py` for one rule:

- `secret` (FAIL): scans rule-file bodies (frontmatter skipped) for six
  well-known API-key shapes and for credential-shaped variable
  assignments. Obvious placeholder values (`your-`, `example`,
  `placeholder`, `todo`, `foo`/`bar`/`baz`, etc.) are excluded from the
  generic credential match.

Exit codes:
  0  — overall_status pass / inapplicable
  1  — overall_status=fail
  64 — usage error

Example:
    ./scan_secrets.py .claude/rules/
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
RULE_ID = "secret"

KNOWN_PATTERNS: dict[str, re.Pattern[str]] = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHub personal access token": re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "GitHub fine-grained PAT": re.compile(r"github_pat_[A-Za-z0-9_]{82}"),
    "OpenAI API key": re.compile(r"sk-[A-Za-z0-9]{48}"),
    "Anthropic API key": re.compile(r"sk-ant-[A-Za-z0-9_-]{80,}"),
    "Stripe live key": re.compile(r"sk_live_[A-Za-z0-9]{24}"),
}

CRED_VAR_RE = re.compile(
    r"(?P<name>password|secret|token|api_key|access_key|private_key)"
    r"\s*[=:]\s*"
    r"(?P<quote>[\"'])(?P<value>[^\"']+)(?P=quote)",
    re.IGNORECASE,
)

PLACEHOLDER_VALUE_RE = re.compile(
    r"^\s*("
    r"your[-_]|example|redacted|null|none|undefined|placeholder|todo|fixme|"
    r"xxx|changeme|change[-_]me|foo|bar|baz|abc|xyz"
    r")",
    re.IGNORECASE,
)
PLACEHOLDER_PREFIX_CHARS = ("$", "{", "<")

_RECIPE_SECRET = (
    "Remove the secret from the rule file, rotate the credential "
    "(assume the value in source is already compromised), and reference "
    "it by env var name or vault path instead. Rule files are committed "
    "to git and loaded automatically by Claude — a secret here has the "
    "same exposure as a secret in any committed config.\n\n"
    "Example:\n"
    "    Use the staging API key `sk-ant-abc123def456...` when testing.\n"
    "      -> Use the staging API key stored in\n"
    "         `$ANTHROPIC_API_KEY_STAGING` (see `.env.staging.example`\n"
    "         for the variable name).\n"
)


def _make_finding(path: Path, name: str, line_no: int) -> dict:
    return emit_json_finding(
        rule_id=RULE_ID,
        status="fail",
        location={"line": line_no, "context": f"{path}: {name}"},
        reasoning=(
            f"Detected {name} pattern at line {line_no} of {path}. "
            "Committed credentials leak via git history, build logs, "
            "and shoulder-surfed terminals. Rule files are loaded "
            "automatically by Claude — same exposure as any committed "
            "config."
        ),
        recommended_changes=_RECIPE_SECRET,
    )


def frontmatter_end_line(lines: list[str]) -> int:
    """1-based line number of the closing ``---`` of frontmatter, else 0."""
    if not lines or lines[0] != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i] == "---":
            return i + 1
    return 0


def looks_like_placeholder(value: str) -> bool:
    if not value:
        return True
    if value[0] in PLACEHOLDER_PREFIX_CHARS:
        return True
    return bool(PLACEHOLDER_VALUE_RE.match(value))


def scan_file(path: Path, findings: list[dict]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"warn: cannot read {path}: {err}", file=sys.stderr)
        return

    lines = text.splitlines()
    fm_end = frontmatter_end_line(lines)

    for idx, line in enumerate(lines, start=1):
        if idx <= fm_end:
            continue
        for name, pattern in KNOWN_PATTERNS.items():
            if pattern.search(line):
                findings.append(_make_finding(path, name, idx))
        for match in CRED_VAR_RE.finditer(line):
            if looks_like_placeholder(match.group("value")):
                continue
            findings.append(
                _make_finding(path, "credential variable assignment", idx)
            )


def iter_targets(targets: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    for target in targets:
        if target.is_file():
            resolved.append(target)
        elif target.is_dir():
            resolved.extend(sorted(target.rglob("*.md")))
        else:
            print(f"error: path not found: {target}", file=sys.stderr)
            raise SystemExit(EXIT_USAGE)
    return resolved


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan Claude Code rule files for committed secrets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Rule files or directories to scan (directories walked for *.md).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        findings: list[dict] = []
        for file_path in iter_targets(args.paths):
            scan_file(file_path, findings)
        envelope = emit_rule_envelope(rule_id=RULE_ID, findings=findings)
        print_envelope([envelope])
        return 1 if envelope["overall_status"] == "fail" else 0
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
