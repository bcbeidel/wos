#!/usr/bin/env python3
"""Tier-1 deterministic check: validate .pre-commit-config.yaml shape.

Emits a JSON ARRAY of four envelopes per `_common.py`:

  - config-missing (FAIL): file exists at the supplied path.
  - yaml-parse (FAIL): file parses as YAML and the top level is a mapping.
  - repos-key (FAIL): top-level `repos:` is a non-empty list.
  - hook-shape (FAIL): every repo / hook entry is a mapping with a string `id:`.

Exit codes:
  0   — all envelopes pass / warn / inapplicable
  1   — any envelope overall_status=fail
  64  — usage error
  69  — missing required dependency (PyYAML)
  130 — interrupted

Example:
    ./check_yaml_shape.py .pre-commit-config.yaml
"""

# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_MISSING_DEP = 69
EXIT_INTERRUPTED = 130

_RULE_ORDER: list[str] = [
    "config-missing",
    "yaml-parse",
    "repos-key",
    "hook-shape",
]

_RECIPE_CONFIG_MISSING = (
    "Run `/build:build-pre-commit-config` to scaffold a fresh config. "
    "An empty or hand-stubbed file obscures the real decision about "
    "which hooks belong in this repo.\n"
)

_RECIPE_YAML_PARSE = (
    "Fix the YAML syntax error named by the parser. Common culprits: "
    "mixed tabs and spaces, unquoted values starting with `*` / `&` / `!`, "
    "unbalanced brackets. An unparseable config means `pre-commit` runs "
    "nothing; every commit silently passes the hook stage.\n"
)

_RECIPE_REPOS_KEY = (
    "Add a `repos:` list at the top level; populate with at least the "
    "`pre-commit-hooks` baseline.\n\n"
    "Example:\n"
    "    repos:\n"
    "      - repo: https://github.com/pre-commit/pre-commit-hooks\n"
    "        rev: v4.6.0\n"
    "        hooks:\n"
    "          - id: trailing-whitespace\n"
    "          - id: end-of-file-fixer\n"
)

_RECIPE_HOOK_SHAPE = (
    "Reformat the entry as a YAML mapping with `repo:` / `hooks:` (for "
    "repo blocks) or a string `id:` (for hook entries). `pre-commit` "
    "rejects malformed entries; depending on version the whole repos "
    "block may be silently skipped.\n"
)

_RECIPES: dict[str, str] = {
    "config-missing": _RECIPE_CONFIG_MISSING,
    "yaml-parse": _RECIPE_YAML_PARSE,
    "repos-key": _RECIPE_REPOS_KEY,
    "hook-shape": _RECIPE_HOOK_SHAPE,
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
) -> bool:
    """Run shape checks against a single config path; return True if a
    structural FAIL means subsequent rules cannot meaningfully run."""
    if not path.exists():
        per_rule["config-missing"].append(
            _make_finding(
                "config-missing",
                "fail",
                f"{path}: config not found",
                f".pre-commit-config.yaml not found at {path}.",
            )
        )
        return True

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as err:
        per_rule["config-missing"].append(
            _make_finding(
                "config-missing",
                "fail",
                f"{path}: cannot read config ({err})",
                f"Cannot read {path}: {err}.",
            )
        )
        return True

    try:
        data = yaml_mod.safe_load(raw)
    except yaml_mod.YAMLError as err:
        per_rule["yaml-parse"].append(
            _make_finding(
                "yaml-parse",
                "fail",
                f"{path}: YAML parse error: {err}",
                f"YAML parse error in {path}: {err}.",
            )
        )
        return True

    if not isinstance(data, dict):
        per_rule["yaml-parse"].append(
            _make_finding(
                "yaml-parse",
                "fail",
                f"{path}: top-level YAML is not a mapping",
                f"Top-level YAML in {path} is not a mapping; the config "
                "must be a mapping with at least a `repos:` key.",
            )
        )
        return True

    repos = data.get("repos")
    if not isinstance(repos, list) or not repos:
        per_rule["repos-key"].append(
            _make_finding(
                "repos-key",
                "fail",
                f"{path}: top-level `repos:` missing or empty",
                f"Top-level `repos:` key missing or empty in {path}.",
            )
        )
        return False

    for ri, repo in enumerate(repos):
        if not isinstance(repo, dict):
            per_rule["hook-shape"].append(
                _make_finding(
                    "hook-shape",
                    "fail",
                    f"{path}: repos[{ri}] is not a mapping",
                    f"repos[{ri}] in {path} is not a mapping; each repo "
                    "entry must be a YAML mapping with `repo:` and `hooks:`.",
                )
            )
            continue

        hooks = repo.get("hooks")
        if not isinstance(hooks, list):
            per_rule["hook-shape"].append(
                _make_finding(
                    "hook-shape",
                    "fail",
                    f"{path}: repos[{ri}] has no `hooks:` list",
                    f"repos[{ri}] in {path} has no `hooks:` list.",
                )
            )
            continue

        for hi, hook in enumerate(hooks):
            if not isinstance(hook, dict):
                per_rule["hook-shape"].append(
                    _make_finding(
                        "hook-shape",
                        "fail",
                        f"{path}: repos[{ri}].hooks[{hi}] is not a mapping",
                        f"repos[{ri}].hooks[{hi}] in {path} is not a "
                        "mapping; each hook entry must be a YAML mapping "
                        "with at least an `id:` key.",
                    )
                )
                continue
            hook_id = hook.get("id")
            if not isinstance(hook_id, str) or not hook_id.strip():
                per_rule["hook-shape"].append(
                    _make_finding(
                        "hook-shape",
                        "fail",
                        f"{path}: repos[{ri}].hooks[{hi}] missing string `id:`",
                        f"repos[{ri}].hooks[{hi}] in {path} is missing a "
                        "non-empty string `id:`.",
                    )
                )

    return False


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_yaml_shape.py",
        description="Validate .pre-commit-config.yaml shape (Tier-1 deterministic check).",  # noqa: E501
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
