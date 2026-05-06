#!/usr/bin/env python3
"""Tier-1 deterministic check: verify .pre-commit-config.yaml `rev:` pinning.

Emits a JSON ARRAY of two envelopes per `_common.py`:

  - floating-rev (FAIL): `rev:` is a floating ref
    (main / master / HEAD / develop / latest / stable).
  - rev-shape (WARN): `rev:` is neither a semver tag (vX.Y.Z) nor a
    40-char SHA.

Exit codes:
  0   — all envelopes pass / warn / inapplicable
  1   — any envelope overall_status=fail
  64  — usage error
  69  — missing required dependency (PyYAML)
  130 — interrupted

Example:
    ./check_rev_pinning.py .pre-commit-config.yaml
"""

# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_MISSING_DEP = 69
EXIT_INTERRUPTED = 130

FLOATING_REFS = frozenset({"main", "master", "HEAD", "develop", "latest", "stable"})
SEMVER_TAG = re.compile(r"^v?\d+\.\d+(\.\d+)?([-.].+)?$")
SHA_40 = re.compile(r"^[0-9a-f]{40}$")

_RULE_ORDER: list[str] = ["floating-rev", "rev-shape"]

_RECIPE_FLOATING_REV = (
    "Replace the floating ref with an immutable tag or 40-char SHA. "
    "Easiest path: run `pre-commit autoupdate` to pin to the current "
    "stable tag.\n\n"
    "Example:\n"
    "    rev: main\n"
    "      -> rev: v0.6.9\n\n"
    "Floating refs produce different hook versions on different "
    "machines and at different times — the config stops being "
    "reproducible.\n"
)

_RECIPE_REV_SHAPE = (
    "Resolve to a versioned tag (`vX.Y.Z`) or a 40-char commit SHA. "
    "Date tags and short SHAs are immutable but lose intent (release "
    "boundary vs exact commit).\n\n"
    "Example:\n"
    "    rev: \"2024-01-15\"\n"
    "      -> rev: v4.6.0\n"
)

_RECIPES: dict[str, str] = {
    "floating-rev": _RECIPE_FLOATING_REV,
    "rev-shape": _RECIPE_REV_SHAPE,
}


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


def _check_config(
    path: Path, yaml_mod, per_rule: dict[str, list[dict]]
) -> None:
    try:
        data = yaml_mod.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml_mod.YAMLError):
        # check_yaml_shape.py owns these FAILs; stay silent here.
        return

    if not isinstance(data, dict):
        return
    repos = data.get("repos")
    if not isinstance(repos, list):
        return

    for ri, repo in enumerate(repos):
        if not isinstance(repo, dict):
            continue
        if repo.get("repo") == "local":
            continue
        rev = repo.get("rev")
        if not isinstance(rev, str):
            continue

        if rev in FLOATING_REFS:
            per_rule["floating-rev"].append(
                _make_finding(
                    "floating-rev",
                    "fail",
                    f"{path}: repos[{ri}] rev: {rev!r}",
                    f"repos[{ri}] in {path} pins rev: {rev!r}, a "
                    "floating ref. Floating refs break reproducibility.",
                )
            )
            continue

        if not (SEMVER_TAG.match(rev) or SHA_40.match(rev)):
            per_rule["rev-shape"].append(
                _make_finding(
                    "rev-shape",
                    "warn",
                    f"{path}: repos[{ri}] rev: {rev!r}",
                    f"repos[{ri}] in {path} pins rev: {rev!r}, neither "
                    "a semver tag nor a 40-char SHA.",
                )
            )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_rev_pinning.py",
        description="Audit .pre-commit-config.yaml `rev:` pins (Tier-1 deterministic check).",  # noqa: E501
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more paths to .pre-commit-config.yaml files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)

    try:
        import yaml
    except ImportError:
        print(
            "error: PyYAML required. Install via `pip install pyyaml`.",
            file=sys.stderr,
        )
        return EXIT_MISSING_DEP

    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        for p in args.paths:
            _check_config(p, yaml, per_rule)
        envelopes = [
            emit_rule_envelope(rule_id=r, findings=per_rule[r])
            for r in _RULE_ORDER
        ]
        print_envelope(envelopes)
        any_fail = any(e["overall_status"] == "fail" for e in envelopes)
        return 1 if any_fail else 0
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
