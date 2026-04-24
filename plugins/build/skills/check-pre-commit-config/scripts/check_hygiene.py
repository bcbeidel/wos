#!/usr/bin/env python3
"""Tier-1 deterministic check: hygiene patterns for .pre-commit-config.yaml.

Checks:
  - minimum_pre_commit_version present (WARN)
  - language-specific hooks pin language_version or have default_language_version (WARN)
  - every hook has a non-empty `id:` (FAIL)
  - every `repo: local` hook has a human-readable `name:` (WARN)
  - file-mutating hooks declare `require_serial: true` (WARN)
  - no local hook reimplements a built-in `pre-commit-hooks` check (WARN)

Exit codes: 0 clean/WARN, 1 one or more FAIL, 2 usage error, 69 missing
PyYAML, 130 interrupted.

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

EXIT_FAIL = 1
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


def emit(
    severity: str, path: Path, check: str, detail: str, recommendation: str
) -> None:
    print(f"{severity}  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def looks_like_mutator(hook: dict) -> bool:
    hook_id = hook.get("id", "")
    if isinstance(hook_id, str) and hook_id in MUTATOR_IDS:
        return True
    args = hook.get("args")
    if isinstance(args, list):
        flat = " ".join(str(a) for a in args)
        if any(hint in flat for hint in MUTATOR_ARG_HINTS):
            return True
    return False


def check_config(path: Path, yaml_mod) -> int:
    try:
        data = yaml_mod.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml_mod.YAMLError):
        return 0

    if not isinstance(data, dict):
        return 0

    fails = 0

    if "minimum_pre_commit_version" not in data:
        emit(
            "WARN",
            path,
            "min-version",
            "top-level `minimum_pre_commit_version` missing",
            'Add `minimum_pre_commit_version: "<version>"` matching the version CI tests.',  # noqa: E501
        )

    default_lang = data.get("default_language_version")
    covered_languages: set[str] = set()
    if isinstance(default_lang, dict):
        covered_languages = {k for k in default_lang if isinstance(k, str)}

    repos = data.get("repos")
    if not isinstance(repos, list):
        return fails

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
                emit(
                    "FAIL",
                    path,
                    "hook-id",
                    f"repos[{ri}].hooks[{hi}] missing `id:`",
                    "Add a kebab-case `id:` naming what the hook does.",
                )
                fails += 1
                continue

            if is_local:
                name = hook.get("name")
                if not isinstance(name, str) or not name.strip():
                    emit(
                        "WARN",
                        path,
                        "local-hook-name",
                        f"`repo: local` hook {hook_id!r} missing human-readable `name:`",  # noqa: E501
                        "Add a `name:` that reads well in failure output.",
                    )

                lang = hook.get("language")
                if isinstance(lang, str) and lang in PINNED_LANGUAGES:
                    has_hook_pin = "language_version" in hook
                    has_default = lang in covered_languages
                    if not (has_hook_pin or has_default):
                        emit(
                            "WARN",
                            path,
                            "lang-version-pin",
                            f"hook {hook_id!r} uses language: {lang!r} without `language_version` pin",  # noqa: E501
                            f"Add `language_version:` to the hook or `default_language_version.{lang}:` at the top level.",  # noqa: E501
                        )

                if hook_id in BUILTIN_HOOK_IDS:
                    emit(
                        "WARN",
                        path,
                        "builtin-duplication",
                        f"local hook {hook_id!r} reimplements a built-in `pre-commit-hooks` check",  # noqa: E501
                        f"Remove the local hook; use the upstream `{hook_id}` from pre-commit/pre-commit-hooks.",  # noqa: E501
                    )

            if looks_like_mutator(hook):
                if not hook.get("require_serial"):
                    emit(
                        "WARN",
                        path,
                        "require-serial",
                        f"file-mutating hook {hook_id!r} missing `require_serial: true`",  # noqa: E501
                        "Add `require_serial: true` to prevent race conditions on shared files.",  # noqa: E501
                    )

    return fails


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit pre-commit hygiene patterns (Tier-1 deterministic check).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        total = sum(check_config(p, yaml) for p in args.paths)
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED

    return EXIT_FAIL if total else 0


if __name__ == "__main__":
    sys.exit(main())
