#!/usr/bin/env python3
"""Tier-1 README secrets scanner.

Emits a JSON ARRAY containing one envelope per `_common.py` for one rule:

- `secret` (FAIL): scans README bodies (frontmatter skipped) for named
  API-key shapes (AWS, GitHub, OpenAI, Anthropic, Stripe), credential-
  shaped variable assignments inside fenced code blocks (placeholders
  excluded), and internal/private hostnames (`.corp.`, `.internal.`,
  `.prod.`, `.prd.`, `.intranet.`).

A FAIL excludes the file from Tier-2 judgment.

Exit codes:
  0  — overall_status pass / inapplicable
  1  — overall_status=fail
  64 — usage error

Example:
    ./check_secrets.py README.md path/to/docs/
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

RULE_ID = "secret"
_RULE_ORDER: list[str] = [RULE_ID]

_RECIPE_SECRET = (
    "Remove the secret from the README, rotate the credential (assume any "
    "value committed to source is already compromised), and reference it "
    "via an env-var name or vault path. Replace the value in the example "
    "with a clearly-marked placeholder.\n\n"
    "Example:\n"
    '    export API_KEY="sk-proj-abc123def456"\n'
    '      -> export API_KEY="<YOUR_OPENAI_API_KEY>"   # set to your key\n'
)

_RECIPES: dict[str, str] = {RULE_ID: _RECIPE_SECRET}


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


def _is_placeholder(value: str) -> bool:
    return value.lower().startswith(_PLACEHOLDER_VALUE_PREFIXES)


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_secrets.py: cannot read {path}: {err}", file=sys.stderr)
        return
    lines = _strip_frontmatter(raw)
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
                per_rule[RULE_ID].append(
                    _make_finding(
                        RULE_ID,
                        "fail",
                        f"{path}: {name}",
                        f"Detected {name} pattern at line {lineno} of "
                        f"{path}. Committed credentials leak via git "
                        "history, archives, and forks. README files are "
                        "rendered on every fork view.",
                        line=lineno,
                    )
                )
        if in_fence:
            cred = _CREDENTIAL_VAR_RE.search(line)
            if cred and not _is_placeholder(cred.group("value")):
                per_rule[RULE_ID].append(
                    _make_finding(
                        RULE_ID,
                        "fail",
                        f"{path}: credential variable assignment",
                        f"Credential variable assignment with non-placeholder "
                        f"value at line {lineno} of {path}.",
                        line=lineno,
                    )
                )
        if _INTERNAL_HOST_RE.search(line):
            per_rule[RULE_ID].append(
                _make_finding(
                    RULE_ID,
                    "fail",
                    f"{path}: internal hostname",
                    f"Internal/private hostname detected at line {lineno} "
                    f"of {path}. Internal infra topology should not appear "
                    "in published README content.",
                    line=lineno,
                )
            )


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
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        files = _collect_targets(args.paths)
        for f in files:
            _scan_file(f, per_rule)
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
