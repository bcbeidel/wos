#!/usr/bin/env python3
"""Tier-1 bash naming checker — promotes the former D6 rule to scripted detection.

Single rule: rule_id="naming". All findings are status="warn" (style coaching).
Detects three mechanically-detectable naming patterns:

  - Capitalized local           — `local Tmp=...` (snake_case violation)
  - Builtin shadowing           — `local set=...`, `local echo=...`, etc.
  - Weak-name function blocklist — `do_stuff()`, `process()`, `handler()`,
                                   `helper()`, `util()`, `misc()`, etc.

Coverage gap (~30%): the script does NOT detect:
  - Single-letter variables at module scope (`x=42` outside loops)
  - Module constants in lowercase (`timeout=30` at top level)
  - Subjective intent-naming weaknesses beyond the weak-name blocklist
The judgment-mode D6 rule used to cover these via LLM. Per the
single-artifact-per-rule discipline, those gaps are now an accepted
cost — a human review or downstream tool catches the residue.

Exit codes:
  0 — overall_status pass / warn (WARN-only script)
  64 — usage error

Example:
    ./check_naming.py path/to/script.sh path/to/scripts/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
RULE_ID = "naming"
EMIT_CAP_PER_FILE = 5

_BASH_SHEBANGS = ("#!/usr/bin/env bash", "#!/bin/bash", "#!/usr/bin/env -S bash")
_BASH_EXTENSIONS = (".sh", ".bash")

# Capitalized local: `local Tmp=`, `local FOO=` (uppercase first letter,
# at least one identifier char follows).
_CAPITALIZED_LOCAL_RE = re.compile(r"^\s*local\s+([A-Z]\w*)\s*=")

# Builtin shadowing — locals named after shell builtins/keywords.
_BUILTIN_NAMES = (
    "local",
    "set",
    "echo",
    "printf",
    "read",
    "unset",
    "export",
    "declare",
    "readonly",
    "alias",
    "trap",
    "exit",
    "return",
    "shift",
    "test",
    "true",
    "false",
    "type",
    "builtin",
    "command",
    "eval",
    "exec",
)
_BUILTIN_SHADOWING_RE = re.compile(
    r"^\s*local\s+(" + "|".join(_BUILTIN_NAMES) + r")\s*="
)

# Weak-name function blocklist — function definitions matching the list.
_WEAK_FUNCTION_NAMES = (
    "do_stuff",
    "do_thing",
    "do_it",
    "do_work",
    "process",
    "process_it",
    "handler",
    "handle",
    "helper",
    "util",
    "utility",
    "misc",
    "run_it",
    "stuff",
)
_WEAK_FUNCTION_RE = re.compile(
    r"^\s*(?:function\s+)?(" + "|".join(_WEAK_FUNCTION_NAMES) + r")\s*\(\s*\)"
)

_RECIPE_CASE = (
    "Use `snake_case` for local variables (`raw_records`, `row_count`), and "
    "`UPPERCASE` for exported env vars and module-level `readonly` constants "
    "(`TIMEOUT`, `LOG_DIR`, `OPENAI_API_KEY`). The case convention signals "
    "scope at a glance.\n\n"
    "Example:\n"
    "    some_function() {\n"
    "      local raw_records\n"
    "      raw_records=\"$(get_data)\"\n"
    "      local row_count\n"
    "      row_count=\"$(count \"$raw_records\")\"\n"
    "    }\n"
)

_RECIPE_SHADOWING = (
    "Avoid names that shadow shell builtins (`local`, `set`, `echo`, `printf`, "
    "`read`, `unset`, `export`, `declare`, `readonly`, `trap`, `exit`, "
    "`return`, `shift`, `test`, `true`, `false`, `type`, `builtin`, `command`, "
    "`eval`, `exec`). Shadowing produces confusing scripts where reading "
    "\"echo\" no longer means what it usually does.\n\n"
    "Example:\n"
    "    # Before (shadows the shell builtin)\n"
    "    local echo=\"hello\"\n"
    "    # After (different name)\n"
    "    local greeting=\"hello\"\n"
)

_RECIPE_WEAK_NAME = (
    "Function names should state intent specifically enough that a reader "
    "can predict behavior without diving into the body. `do_stuff`, "
    "`process`, `handler`, `util`, `misc` force re-derivation from the "
    "function body — and a reader scanning the script learns nothing.\n\n"
    "Examples (renames):\n"
    "    do_stuff()    →  fetch_records() / transform_csv() / write_archive()\n"
    "    process()     →  rotate_logs() / parse_input() / index_files()\n"
    "    handler()     →  on_sigterm() / handle_403() / dispatch_command()\n"
    "    helper()      →  format_path() / split_csv() / parse_iso_date()\n"
)


class _UsageError(Exception):
    pass


def _is_bash_script(path: Path) -> bool:
    if path.suffix in _BASH_EXTENSIONS:
        return True
    try:
        first = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    if not first:
        return False
    return any(first[0] == s or first[0].startswith(s) for s in _BASH_SHEBANGS)


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_bash_script(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_bash_script(child):
                    files.append(child)
        else:
            print(f"check_naming.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _scan_file(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_naming.py: cannot read {path}: {err}", file=sys.stderr)
        return []
    findings: list[dict] = []
    emitted = 0
    for lineno, line in enumerate(lines, 1):
        if emitted >= EMIT_CAP_PER_FILE:
            break
        if line.lstrip().startswith("#"):
            continue
        # Test builtin-shadowing first (it's a stricter subset of "local NAME=").
        m_shadow = _BUILTIN_SHADOWING_RE.match(line)
        if m_shadow:
            findings.append(
                emit_json_finding(
                    rule_id=RULE_ID,
                    status="warn",
                    location={
                        "line": lineno,
                        "context": f"{path}: local {m_shadow.group(1)}=...",
                    },
                    reasoning=(
                        f"line {lineno} declares `local {m_shadow.group(1)}=...` "
                        "— shadows a shell builtin/keyword. Reading this script "
                        "is confusing because the name no longer means what it "
                        "usually does."
                    ),
                    recommended_changes=_RECIPE_SHADOWING,
                )
            )
            emitted += 1
            continue
        m_case = _CAPITALIZED_LOCAL_RE.match(line)
        if m_case:
            findings.append(
                emit_json_finding(
                    rule_id=RULE_ID,
                    status="warn",
                    location={
                        "line": lineno,
                        "context": f"{path}: local {m_case.group(1)}=...",
                    },
                    reasoning=(
                        f"line {lineno} uses capitalized local `{m_case.group(1)}` "
                        "— locals should be `snake_case`. UPPERCASE is reserved "
                        "for exported env vars and module-level `readonly` "
                        "constants."
                    ),
                    recommended_changes=_RECIPE_CASE,
                )
            )
            emitted += 1
            continue
        m_weak = _WEAK_FUNCTION_RE.match(line)
        if m_weak:
            findings.append(
                emit_json_finding(
                    rule_id=RULE_ID,
                    status="warn",
                    location={
                        "line": lineno,
                        "context": f"{path}: {m_weak.group(1)}() definition",
                    },
                    reasoning=(
                        f"line {lineno} defines `{m_weak.group(1)}()` — a "
                        "weak/non-specific function name. The reader cannot "
                        "predict behavior without diving into the body."
                    ),
                    recommended_changes=_RECIPE_WEAK_NAME,
                )
            )
            emitted += 1
    return findings


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_naming.py",
        description="Tier-1 bash naming checker (case, shadowing, weak names).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more .sh/.bash files or directories (non-recursive).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        files = _collect_targets(args.paths)
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130

    all_findings: list[dict] = []
    for f in files:
        all_findings.extend(_scan_file(f))

    envelope = emit_rule_envelope(rule_id=RULE_ID, findings=all_findings)
    print_envelope(envelope)
    return 1 if envelope["overall_status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
