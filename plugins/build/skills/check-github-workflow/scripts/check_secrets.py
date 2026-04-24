#!/usr/bin/env python3
"""Tier-1 hardcoded-secret scanner for GitHub Actions workflows.

Flags literal tokens that match well-known credential shapes. Source
text only — does not evaluate expressions. Every finding is FAIL and
excludes the file from Tier-2 judgment (the file carries a live
credential; judgment-level coaching on layout is the wrong coverage).

Example:
    ./check_secrets.py .github/workflows/ci.yml
    ./check_secrets.py .github/workflows/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_WORKFLOW_SUFFIXES = (".yml", ".yaml")

# Anchored credential patterns. Each entry is (label, compiled-regex).
# Regexes match the substring that *is* the credential, not the
# surrounding YAML — the caller frames the finding.
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


def _iter_workflows(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            for suffix in _WORKFLOW_SUFFIXES:
                files.extend(sorted(p.glob(f"*{suffix}")))
        elif p.is_file():
            files.append(p)
    return files


def _scan(path: Path) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"WARN     {path} — read: {exc}", file=sys.stderr)
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Skip lines that are obviously secret *references*, not literals.
        if "${{ secrets." in line or "${{secrets." in line:
            continue
        for label, pattern in _PATTERNS:
            if pattern.search(line):
                findings.append((lineno, label, line.strip()))
                break  # one finding per line is enough
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scan GitHub Actions workflow YAML for hardcoded secrets."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    workflows = _iter_workflows(args.paths)
    if not workflows:
        print("INFO     no workflow files found in provided paths")
        return 0

    had_fail = False
    for path in workflows:
        for lineno, label, snippet in _scan(path):
            had_fail = True
            print(f"FAIL     {path}:{lineno} — secret: {label} detected")
            print(f"         (context) {snippet[:120]}")
            print("  Recommendation: Remove the literal credential from source. "
                  "Replace with ${{ secrets.<NAME> }} referencing a GitHub Secret. "
                  "Rotate the exposed credential immediately — it is in git "
                  "history even after removal.")

    return 1 if had_fail else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
