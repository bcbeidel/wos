#!/usr/bin/env python3
"""Tier-1 deterministic check: safety patterns in pre-commit hooks.

Emits a JSON ARRAY of five envelopes per `_common.py`:

  - network-io (FAIL): network-fetch / dependency-install commands in
    a hook entry or its referenced local script.
  - destructive-git (FAIL): destructive git commands
    (push / commit / reset --hard / clean -fd / rebase / tag /
    update-ref / add).
  - destructive-shell (FAIL): destructive shell commands
    (rm -rf / docker system prune / terraform destroy).
  - sudo (FAIL): privilege escalation (sudo / su -c).
  - error-suppression (FAIL): suppression patterns
    (`|| true` / `--exit-zero` / `set +e`).

Local script files referenced via `entry:` (resolved relative to the
config) are read and scanned; vendored directories are skipped.

Exit codes:
  0   — all envelopes pass / warn / inapplicable
  1   — any envelope overall_status=fail
  64  — usage error
  69  — missing required dependency (PyYAML)
  130 — interrupted

Example:
    ./check_safety.py .pre-commit-config.yaml
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
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_MISSING_DEP = 69
EXIT_INTERRUPTED = 130

VENDORED = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        "vendor",
        "third_party",
    }
)

_RULE_ORDER: list[str] = [
    "network-io",
    "destructive-git",
    "destructive-shell",
    "sudo",
    "error-suppression",
]

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "network-io",
        re.compile(
            r"\b(curl|wget)\b"
            r"|\bpip\s+install\b|\bnpm\s+install\b|\bapt-get\s+install\b"
            r"|\bbrew\s+install\b|\bgem\s+install\b|\bgo\s+get\b|\byarn\s+add\b"
        ),
    ),
    (
        "destructive-git",
        re.compile(
            r"\bgit\s+(push|commit|reset\s+--hard|clean\s+-fd|rebase|tag|update-ref|add)\b"
        ),
    ),
    (
        "destructive-shell",
        re.compile(
            r"\brm\s+-rf\b"
            r"|\bdocker\s+system\s+prune\b"
            r"|\bterraform\s+destroy\b"
        ),
    ),
    (
        "sudo",
        re.compile(r"\bsudo\b|\bsu\s+-c\b"),
    ),
    (
        "error-suppression",
        re.compile(r"\|\|\s*true\b|--exit-zero\b|\bset\s+\+e\b"),
    ),
]

_RECIPE_NETWORK_IO = (
    "Move dependency installation out of the hook. The framework's "
    "language env is the right place: `language: python` with pinned "
    "`language_version` and `additional_dependencies: [...]`. Network "
    "I/O in a hook breaks offline commits and pays a round-trip on "
    "every commit; the framework caches per-language envs.\n"
)

_RECIPE_DESTRUCTIVE_GIT = (
    "Remove the destructive git call. Pre-commit is the wrong layer "
    "for push / tag / reset / `git add` / history rewrites. The "
    "framework re-stages fixer-modified files automatically; explicit "
    "`git add` from inside a hook hides the fixer's diff from the "
    "developer.\n\n"
    "Example:\n"
    "    entry: bash -c 'ruff check --fix && git add .'\n"
    "      -> entry: ruff\n"
    "         args: [--fix]\n"
)

_RECIPE_DESTRUCTIVE_SHELL = (
    "Remove the destructive call. If the script genuinely needs a "
    "scratch directory, use `mktemp -d` + `trap ... EXIT` for cleanup "
    "instead of `rm -rf`. Move repo-wide cleanup to CI, `pre-push`, "
    "or a dedicated maintenance script — commit-time is the wrong "
    "moment to delete or destroy.\n"
)

_RECIPE_SUDO = (
    "Remove the privilege escalation. Hooks run as the developer's "
    "user; password prompts break workflow and silent (passwordless) "
    "`sudo` is a privilege-escalation vector. If elevated privileges "
    "are truly required, move the check to a CI job in a controlled "
    "environment.\n"
)

_RECIPE_ERROR_SUPPRESSION = (
    "Remove the suppression. If the tool legitimately needs a "
    "warning-only mode, configure its native warning level (most "
    "linters support `--warn-only` or a severity setting) rather "
    "than hiding the exit code. Silent pass-through defeats the "
    "hook's purpose.\n\n"
    "Example:\n"
    "    entry: bash -c 'ruff check || true'\n"
    "      -> entry: ruff\n"
)

_RECIPES: dict[str, str] = {
    "network-io": _RECIPE_NETWORK_IO,
    "destructive-git": _RECIPE_DESTRUCTIVE_GIT,
    "destructive-shell": _RECIPE_DESTRUCTIVE_SHELL,
    "sudo": _RECIPE_SUDO,
    "error-suppression": _RECIPE_ERROR_SUPPRESSION,
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


def _scan_text(
    source_path: Path,
    text: str,
    origin: str,
    per_rule: dict[str, list[dict]],
) -> None:
    """Scan text for every pattern; record one finding per match."""
    for line_idx, line in enumerate(text.splitlines(), start=1):
        for check_id, regex in PATTERNS:
            if regex.search(line):
                per_rule[check_id].append(
                    _make_finding(
                        check_id,
                        "fail",
                        f"{source_path}: {origin}:{line_idx}: {line.strip()[:120]}",
                        f"{check_id} pattern matched at {origin}:{line_idx} "
                        f"(referenced from {source_path}).",
                        line=line_idx,
                    )
                )


def _resolve_entry_script(config_path: Path, entry: str) -> Path | None:
    if not entry:
        return None
    tokens = shlex.split(entry, posix=True)
    if not tokens:
        return None
    candidate = Path(tokens[0])
    if candidate.is_absolute():
        return candidate if candidate.is_file() else None
    resolved = (config_path.parent / candidate).resolve()
    if not resolved.is_file():
        return None
    if any(part in VENDORED for part in resolved.parts):
        return None
    return resolved


def _check_config(
    path: Path, yaml_mod, per_rule: dict[str, list[dict]]
) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml_mod.safe_load(raw)
    except (OSError, yaml_mod.YAMLError):
        return

    if not isinstance(data, dict):
        return

    repos = data.get("repos")
    if not isinstance(repos, list):
        return

    seen_scripts: set[Path] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        hooks = repo.get("hooks")
        if not isinstance(hooks, list):
            continue
        for hook in hooks:
            if not isinstance(hook, dict):
                continue
            entry = hook.get("entry")
            if isinstance(entry, str):
                _scan_text(
                    path, entry, f"hook[{hook.get('id', '?')}].entry", per_rule
                )
                script_path = _resolve_entry_script(path, entry)
                if script_path and script_path not in seen_scripts:
                    seen_scripts.add(script_path)
                    try:
                        script_text = script_path.read_text(encoding="utf-8")
                    except OSError:
                        continue
                    _scan_text(path, script_text, str(script_path), per_rule)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_safety.py",
        description="Audit pre-commit safety patterns (Tier-1 deterministic check).",  # noqa: E501
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
