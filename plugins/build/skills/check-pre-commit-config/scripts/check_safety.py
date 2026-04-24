#!/usr/bin/env python3
"""Tier-1 deterministic check: safety patterns in pre-commit hooks.

Scans `entry:` values and referenced local script contents for:
  - network-fetch commands (curl, wget, pip/npm/gem install, etc.)
  - destructive git commands (push, reset --hard, clean -fdx, add, ...)
  - destructive shell commands (rm -rf, docker system prune, terraform destroy)
  - privilege escalation (sudo, su -c)
  - error suppression (|| true, --exit-zero, toggled set +e)

Every match is FAIL. Referenced local scripts (under `entry:` paths
that resolve relative to the config's parent directory) are read and
scanned; scripts under vendored directories are skipped.

Exit codes: 0 clean, 1 one or more FAIL, 2 usage error, 69 missing
PyYAML, 130 interrupted.

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

EXIT_FAIL = 1
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

PATTERNS = [
    # (check_id, regex, recommendation)
    (
        "network-io",
        re.compile(
            r"\b(curl|wget)\b"
            r"|\bpip\s+install\b|\bnpm\s+install\b|\bapt-get\s+install\b"
            r"|\bbrew\s+install\b|\bgem\s+install\b|\bgo\s+get\b|\byarn\s+add\b"
        ),
        "Move dependency installs out of the hook. Use the framework's `additional_dependencies:` or a language env.",  # noqa: E501
    ),
    (
        "destructive-git",
        re.compile(
            r"\bgit\s+(push|commit|reset\s+--hard|clean\s+-fd|rebase|tag|update-ref|add)\b"
        ),
        "Remove the destructive git call. Commit-time is the wrong layer for history mutations or auto-`git add`.",  # noqa: E501
    ),
    (
        "destructive-shell",
        re.compile(
            r"\brm\s+-rf\b"
            r"|\bdocker\s+system\s+prune\b"
            r"|\bterraform\s+destroy\b"
        ),
        "Remove the destructive call. Move cleanup to CI or a dedicated maintenance script.",  # noqa: E501
    ),
    (
        "sudo",
        re.compile(r"\bsudo\b|\bsu\s+-c\b"),
        "Remove privilege escalation. If elevated privileges are truly needed, move the check to CI.",  # noqa: E501
    ),
    (
        "error-suppression",
        re.compile(r"\|\|\s*true\b|--exit-zero\b|\bset\s+\+e\b"),
        "Remove the suppression. Use the tool's native warning severity instead of hiding the exit code.",  # noqa: E501
    ),
]


def emit(
    severity: str, path: Path, check: str, detail: str, recommendation: str
) -> None:
    print(f"{severity}  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def scan_text(source_path: Path, text: str, origin: str) -> int:
    """Scan text for every pattern; emit a FAIL per match. Return fail count."""
    fails = 0
    for line_idx, line in enumerate(text.splitlines(), start=1):
        for check_id, regex, rec in PATTERNS:
            if regex.search(line):
                emit(
                    "FAIL",
                    source_path,
                    check_id,
                    f"{origin}:{line_idx}: {line.strip()[:120]}",
                    rec,
                )
                fails += 1
    return fails


def resolve_entry_script(config_path: Path, entry: str) -> Path | None:
    """If `entry:` refers to a local script file, return its resolved path."""
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


def check_config(path: Path, yaml_mod) -> int:
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml_mod.safe_load(raw)
    except (OSError, yaml_mod.YAMLError):
        return 0

    if not isinstance(data, dict):
        return 0

    fails = 0
    repos = data.get("repos")
    if not isinstance(repos, list):
        return 0

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
                fails += scan_text(path, entry, f"hook[{hook.get('id', '?')}].entry")
                # Also follow the entry to a script file if it resolves.
                script_path = resolve_entry_script(path, entry)
                if script_path and script_path not in seen_scripts:
                    seen_scripts.add(script_path)
                    try:
                        script_text = script_path.read_text(encoding="utf-8")
                    except OSError:
                        continue
                    fails += scan_text(path, script_text, str(script_path))

    return fails


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit pre-commit safety patterns (Tier-1 deterministic check).",
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
