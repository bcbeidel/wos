#!/usr/bin/env python3
"""Tier-1 deterministic check: hygiene patterns for .pre-commit-config.yaml.

Emits a JSON ARRAY of six envelopes per `_common.py`:

  - min-version (WARN): top-level `minimum_pre_commit_version` declared.
  - lang-version-pin (WARN): every language-specific local hook pins
    `language_version` or has a top-level `default_language_version`.
  - hook-id (FAIL): every hook entry has a non-empty string `id:`.
  - local-hook-name (WARN): every `repo: local` hook declares `name:`.
  - require-serial (WARN): file-mutating hooks declare
    `require_serial: true`.
  - builtin-duplication (WARN): no local hook reimplements a built-in
    `pre-commit-hooks` check.

Exit codes:
  0   — all envelopes pass / warn / inapplicable
  1   — any envelope overall_status=fail
  64  — usage error
  69  — missing required dependency (PyYAML)
  130 — interrupted

Example:
    ./check_hygiene.py .pre-commit-config.yaml
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

PINNED_LANGUAGES = frozenset(
    {"python", "node", "ruby", "rust", "golang", "conda", "dotnet"}
)

MUTATOR_IDS = frozenset(
    {
        "black",
        "blacken-docs",
        "ruff-format",
        "isort",
        "prettier",
        "prettier-package-json",
        "gofmt",
        "goimports",
        "rustfmt",
        "shfmt",
        "clang-format",
        "terraform-fmt",
        "terraform_fmt",
        "autopep8",
        "yapf",
    }
)

MUTATOR_ARG_HINTS = ("--fix", "--write", "-w", "-i", "--in-place")

BUILTIN_HOOK_IDS = frozenset(
    {
        "trailing-whitespace",
        "end-of-file-fixer",
        "check-merge-conflict",
        "check-added-large-files",
        "check-yaml",
        "check-json",
        "check-toml",
        "check-xml",
        "check-ast",
        "check-case-conflict",
        "check-executables-have-shebangs",
        "check-shebang-scripts-are-executable",
        "check-symlinks",
        "check-vcs-permalinks",
        "detect-private-key",
        "mixed-line-ending",
        "debug-statements",
        "fix-byte-order-marker",
        "forbid-new-submodules",
        "name-tests-test",
        "no-commit-to-branch",
        "pretty-format-json",
        "requirements-txt-fixer",
        "sort-simple-yaml",
    }
)

_RULE_ORDER: list[str] = [
    "min-version",
    "lang-version-pin",
    "hook-id",
    "local-hook-name",
    "require-serial",
    "builtin-duplication",
]

_RECIPE_MIN_VERSION = (
    "Add `minimum_pre_commit_version` matching the version CI tests.\n\n"
    "Example:\n"
    "    minimum_pre_commit_version: \"3.7.0\"\n\n"
    "    repos:\n"
    "      ...\n\n"
    "Incompatible runner versions produce cryptic errors; declaring "
    "the minimum surfaces the mismatch immediately.\n"
)

_RECIPE_LANG_VERSION_PIN = (
    "Add `default_language_version` at the top, or pin per hook with "
    "`language_version:`.\n\n"
    "Example:\n"
    "    default_language_version:\n"
    "      python: python3.11\n\n"
    "Without the pin, the hook runs against whatever interpreter is "
    "first in `$PATH` — Python 3.9 vs 3.12 can produce different "
    "lint outputs.\n"
)

_RECIPE_HOOK_ID = (
    "Add a kebab-case `id:` naming what the hook does. `pre-commit` "
    "requires `id` for every hook; missing-id entries are silently "
    "skipped in some framework versions.\n"
)

_RECIPE_LOCAL_HOOK_NAME = (
    "Add a `name:` that reads well in failure output.\n\n"
    "Example:\n"
    "    - id: validate-schema\n"
    "      + name: validate jsonschema contract\n"
    "        entry: scripts/hooks/validate_schema.py\n\n"
    "When this hook fails, the developer sees `name:`. A missing "
    "name falls back to `id:`, which is usually terser than useful.\n"
)

_RECIPE_REQUIRE_SERIAL = (
    "Add `require_serial: true` to any hook known to mutate files. "
    "Parallel file-mutating hooks race on shared files — intermittent "
    "corruption that only surfaces under load.\n\n"
    "Example:\n"
    "    - id: black\n"
    "      args: [--safe]\n"
    "      + require_serial: true\n"
)

_RECIPE_BUILTIN_DUPLICATION = (
    "Remove the local hook; use the upstream "
    "`pre-commit/pre-commit-hooks` equivalent. Local reimplementations "
    "drift, miss edge cases the upstream handles, and waste "
    "maintenance effort.\n"
)

_RECIPES: dict[str, str] = {
    "min-version": _RECIPE_MIN_VERSION,
    "lang-version-pin": _RECIPE_LANG_VERSION_PIN,
    "hook-id": _RECIPE_HOOK_ID,
    "local-hook-name": _RECIPE_LOCAL_HOOK_NAME,
    "require-serial": _RECIPE_REQUIRE_SERIAL,
    "builtin-duplication": _RECIPE_BUILTIN_DUPLICATION,
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


def _looks_like_mutator(hook: dict) -> bool:
    hook_id = hook.get("id", "")
    if isinstance(hook_id, str) and hook_id in MUTATOR_IDS:
        return True
    args = hook.get("args")
    if isinstance(args, list):
        flat = " ".join(str(a) for a in args)
        if any(hint in flat for hint in MUTATOR_ARG_HINTS):
            return True
    return False


def _check_config(
    path: Path, yaml_mod, per_rule: dict[str, list[dict]]
) -> None:
    try:
        data = yaml_mod.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml_mod.YAMLError):
        return

    if not isinstance(data, dict):
        return

    if "minimum_pre_commit_version" not in data:
        per_rule["min-version"].append(
            _make_finding(
                "min-version",
                "warn",
                f"{path}: top-level `minimum_pre_commit_version` missing",
                f"Top-level `minimum_pre_commit_version` is missing in {path}.",
            )
        )

    default_lang = data.get("default_language_version")
    covered_languages: set[str] = set()
    if isinstance(default_lang, dict):
        covered_languages = {k for k in default_lang if isinstance(k, str)}

    repos = data.get("repos")
    if not isinstance(repos, list):
        return

    for ri, repo in enumerate(repos):
        if not isinstance(repo, dict):
            continue
        is_local = repo.get("repo") == "local"
        hooks = repo.get("hooks")
        if not isinstance(hooks, list):
            continue
        for hi, hook in enumerate(hooks):
            if not isinstance(hook, dict):
                continue

            hook_id = hook.get("id")
            if not isinstance(hook_id, str) or not hook_id.strip():
                per_rule["hook-id"].append(
                    _make_finding(
                        "hook-id",
                        "fail",
                        f"{path}: repos[{ri}].hooks[{hi}] missing `id:`",
                        f"repos[{ri}].hooks[{hi}] in {path} is missing "
                        "a non-empty string `id:`.",
                    )
                )
                continue

            if is_local:
                name = hook.get("name")
                if not isinstance(name, str) or not name.strip():
                    per_rule["local-hook-name"].append(
                        _make_finding(
                            "local-hook-name",
                            "warn",
                            f"{path}: local hook {hook_id!r} missing `name:`",
                            f"`repo: local` hook {hook_id!r} in {path} "
                            "has no human-readable `name:`.",
                        )
                    )

                lang = hook.get("language")
                if isinstance(lang, str) and lang in PINNED_LANGUAGES:
                    has_hook_pin = "language_version" in hook
                    has_default = lang in covered_languages
                    if not (has_hook_pin or has_default):
                        per_rule["lang-version-pin"].append(
                            _make_finding(
                                "lang-version-pin",
                                "warn",
                                f"{path}: hook {hook_id!r} language: {lang!r} unpinned",  # noqa: E501
                                f"Hook {hook_id!r} in {path} uses "
                                f"language: {lang!r} without a "
                                "`language_version` pin.",
                            )
                        )

                if hook_id in BUILTIN_HOOK_IDS:
                    per_rule["builtin-duplication"].append(
                        _make_finding(
                            "builtin-duplication",
                            "warn",
                            f"{path}: local hook {hook_id!r} duplicates built-in",
                            f"Local hook {hook_id!r} in {path} "
                            "reimplements a built-in `pre-commit-hooks` "
                            "check.",
                        )
                    )

            if _looks_like_mutator(hook):
                if not hook.get("require_serial"):
                    per_rule["require-serial"].append(
                        _make_finding(
                            "require-serial",
                            "warn",
                            f"{path}: mutator {hook_id!r} missing `require_serial: true`",  # noqa: E501
                            f"File-mutating hook {hook_id!r} in {path} "
                            "is missing `require_serial: true`.",
                        )
                    )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_hygiene.py",
        description="Audit pre-commit hygiene patterns (Tier-1 deterministic check).",  # noqa: E501
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
