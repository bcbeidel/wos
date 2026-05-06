#!/usr/bin/env python3
"""Tier-1 hardcoded-secret scanner for GitHub Actions workflows.

Emits a JSON ARRAY with a single envelope (rule_id="secret", FAIL).

Flags literal tokens that match well-known credential shapes. Source
text only — does not evaluate expressions.

Exit codes:
  0   — overall_status pass / inapplicable
  1   — overall_status fail
  64  — usage error

Example:
    ./check_secrets.py .github/workflows/ci.yml
    ./check_secrets.py .github/workflows/
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

_WORKFLOW_SUFFIXES = (".yml", ".yaml")

_RULE_ORDER: list[str] = ["secret"]

_RECIPE_SECRET = (
    "Remove the literal credential from workflow source. Replace with "
    "a `${{ secrets.<NAME> }}` reference to a GitHub Secret configured "
    "in the repository or environment. Rotate the exposed credential — "
    "its prior presence in git history means it cannot be trusted "
    "going forward.\n\n"
    "Example:\n"
    "    env:\n"
    "      API_KEY: sk-proj-abc123def456...\n"
    "      -> env:\n"
    "           API_KEY: ${{ secrets.OPENAI_API_KEY }}\n"
)

_RECIPES: dict[str, str] = {"secret": _RECIPE_SECRET}

# Anchored credential patterns. Each entry is (label, compiled-regex).
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "AWS secret access key",
        re.compile(r"\b[A-Za-z0-9/+=]{40}\b(?=.*aws)", re.IGNORECASE),
    ),
    ("GitHub PAT", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("GitHub OAuth", re.compile(r"\bgho_[A-Za-z0-9]{36}\b")),
    ("GitHub App token", re.compile(r"\b(?:ghu|ghs)_[A-Za-z0-9]{36}\b")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Stripe live key", re.compile(r"\b(?:sk|rk)_live_[0-9a-zA-Z]{24,}\b")),
    (
        "PEM private key",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----"),
    ),
    (
        "JWT",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
    ),
    ("HTTP basic auth in URL", re.compile(r"https?://[^\s:@/]+:[^\s@/]+@[^\s/]+")),
)


class _UsageError(Exception):
    pass


def _iter_workflows(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            for suffix in _WORKFLOW_SUFFIXES:
                files.extend(sorted(p.glob(f"*{suffix}")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"check_secrets.py: path not found: {p}", file=sys.stderr)
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


def _scan(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"check_secrets.py: cannot read {path}: {exc}", file=sys.stderr)
        return
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Skip lines that are obviously secret *references*, not literals.
        if "${{ secrets." in line or "${{secrets." in line:
            continue
        for label, pattern in _PATTERNS:
            if pattern.search(line):
                snippet = line.strip()[:120]
                per_rule["secret"].append(
                    _make_finding(
                        "secret",
                        "fail",
                        f"{path}:{lineno}: {label}",
                        f"Line {lineno} of {path}: {label} detected — "
                        f"`{snippet}`. Hardcoded credentials leak through "
                        "git history, logs, artifacts, and forks.",
                        line=lineno,
                    )
                )
                break  # one finding per line is enough


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_secrets.py",
        description="Scan GitHub Actions workflow YAML for hardcoded secrets.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more workflow .yml/.yaml files or directories.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        files = _iter_workflows(args.paths)
        for path in files:
            _scan(path, per_rule)
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
