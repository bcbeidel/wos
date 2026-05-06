#!/usr/bin/env python3
"""Tier-1 bash structural checker — emits JSON ARRAY of seven envelopes.

Seven structural sub-checks against each target:
  - shebang (FAIL):             must be `#!/usr/bin/env bash` or `#!/bin/bash`.
  - strict-mode (FAIL):         `set -euo pipefail` in prologue.
  - header-comment (WARN):      >=3 comment lines in first 10 lines.
  - main-fn (WARN):             a `main` function is defined.
  - main-guard (WARN):          BASH_SOURCE sourceable guard present.
  - readonly-config (WARN):     top-level constants declared `readonly`.
  - mktemp-trap-pairing (WARN): every mktemp preceded by a `trap ... EXIT`.

Emits 7 envelopes (one per rule_id) in a JSON array, regardless of which
rules fired. Empty findings → overall_status=pass.

Exit codes:
  0  — overall_status pass / warn for every emitted envelope
  1  — overall_status=fail (shebang or strict-mode failures)
  64 — usage error

Example:
    ./check_structure.py path/to/script.sh path/to/scripts/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
HEADER_WINDOW = 10
MIN_HEADER_COMMENTS = 3
STRICT_MODE_WINDOW = 20

_BASH_SHEBANGS = ("#!/usr/bin/env bash", "#!/bin/bash", "#!/usr/bin/env -S bash")
_BASH_EXTENSIONS = (".sh", ".bash")

_STRICT_MODE_REGEXES = (
    re.compile(r"set\s+-[Ee]?[Eaeux]*o?\s+pipefail"),
    re.compile(r"set\s+-o\s+errexit"),
)

_MAIN_FN_RE = re.compile(r"^(?:function\s+)?main\s*\(\s*\)")
_MAIN_GUARD_RE = re.compile(
    r"\$\{BASH_SOURCE\[0\]\}.*==.*\$\{?0\}?"
    r"|\$\{?0\}?.*==.*\$\{BASH_SOURCE\[0\]\}"
)
_UPPERCASE_ASSIGN_RE = re.compile(r"^[A-Z][A-Z0-9_]+=")
_READONLY_DECL_RE = re.compile(r"^readonly\s")
_MKTEMP_RE = re.compile(r"(?:^|[\s;|])mktemp(?:\s|$)")
_TRAP_EXIT_RE = re.compile(r"^\s*trap\s+.*EXIT")

_RECIPE_SHEBANG = (
    "First line must be exactly `#!/usr/bin/env bash` (or `#!/bin/bash` only "
    "in tightly controlled environments where /bin/bash is guaranteed at 4.0+). "
    "Never `#!/bin/sh` — bash-only constructs (arrays, `[[ ]]`, `local`) silently "
    "fail under dash/BusyBox.\n\n"
    "Example:\n"
    "    #!/usr/bin/env bash\n"
)

_RECIPE_STRICT_MODE = (
    "Add `set -euo pipefail` as the first executable line after the shebang "
    "and header. Use `set -Eeuo pipefail` when installing an ERR trap. "
    "Strict mode turns silent failures, unset-variable typos, and "
    "mid-pipeline errors into loud, early exits.\n\n"
    "Example:\n"
    "    #!/usr/bin/env bash\n"
    "    set -euo pipefail\n"
)

_RECIPE_HEADER_COMMENT = (
    "Add a 5–10 line comment block after the shebang naming purpose, "
    "usage signature, dependencies, and exit codes.\n\n"
    "Example:\n"
    "    #!/usr/bin/env bash\n"
    "    #\n"
    "    # rotate-logs — Compress logs older than 30 days.\n"
    "    #\n"
    "    # Usage:\n"
    "    #   rotate-logs.sh [--dry-run] <log-dir>\n"
    "    #\n"
    "    # Dependencies: gzip, find\n"
    "    #\n"
    "    # Exit codes: 0 success, 1 failure, 64 usage error\n"
)

_RECIPE_MAIN_FN = (
    "Wrap top-level execution in `main() { ... }`; use `${1:?usage: ...}` "
    "for required positionals; call from the sourceable guard at EOF. "
    "A flat top-level script is not testable.\n\n"
    "Example:\n"
    "    main() {\n"
    "      local input=\"${1:?usage: script <input>}\"\n"
    "      process \"$input\"\n"
    "    }\n"
    "    [[ \"${BASH_SOURCE[0]}\" == \"${0}\" ]] && main \"$@\"\n"
)

_RECIPE_MAIN_GUARD = (
    "Add `[[ \"${BASH_SOURCE[0]}\" == \"${0}\" ]] && main \"$@\"` as the last "
    "non-comment line. The guard lets the file be sourced (loading functions) "
    "without invoking main — required for testing with bats/shunit2.\n\n"
    "Example:\n"
    "    [[ \"${BASH_SOURCE[0]}\" == \"${0}\" ]] && main \"$@\"\n"
)

_RECIPE_READONLY_CONFIG = (
    "Prefix every top-level UPPERCASE constant with `readonly`. Readers "
    "should see configuration at the top; `readonly` makes accidental "
    "reassignment a hard error. For env-derived secrets, combine with "
    "`${VAR:?msg}`.\n\n"
    "Example:\n"
    "    readonly TIMEOUT=30\n"
    "    readonly LOG_DIR=\"${LOG_DIR:-/var/log/myapp}\"\n"
    "    readonly API_KEY=\"${OPENAI_API_KEY:?OPENAI_API_KEY env var required}\"\n"
)

_RECIPE_MKTEMP_TRAP = (
    "Capture the `mktemp` path in a variable and register `trap 'rm -rf "
    "\"$path\"' EXIT INT TERM` on the very next line. One trap can list "
    "multiple paths. Without the trap, set -e exits leave orphaned temp "
    "state across runs.\n\n"
    "Example:\n"
    "    tmpdir=\"$(mktemp -d)\"\n"
    "    trap 'rm -rf \"$tmpdir\"' EXIT INT TERM\n"
)

_RULE_ORDER = [
    "shebang",
    "strict-mode",
    "header-comment",
    "main-fn",
    "main-guard",
    "readonly-config",
    "mktemp-trap-pairing",
]


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
            print(f"check_structure.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _scan_shebang(path: Path, lines: list[str]) -> list[dict]:
    first = lines[0] if lines else ""
    if first in ("#!/usr/bin/env bash", "#!/bin/bash") or first.startswith(
        "#!/usr/bin/env -S bash"
    ):
        return []
    return [
        emit_json_finding(
            rule_id="shebang",
            status="fail",
            location={"line": 1, "context": f"{path}: {first[:80]!r}"},
            reasoning=(
                f"First line is {first!r}, not a bash shebang. The skill is "
                "bash-only; non-bash shebangs invite silent dialect failures."
            ),
            recommended_changes=_RECIPE_SHEBANG,
        )
    ]


def _scan_strict_mode(path: Path, lines: list[str]) -> list[dict]:
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
        if any(r.search(line) for r in _STRICT_MODE_REGEXES):
            return []
        if count >= STRICT_MODE_WINDOW:
            break
    return [
        emit_json_finding(
            rule_id="strict-mode",
            status="fail",
            location={"line": 1, "context": f"{path}: prologue"},
            reasoning=(
                "`set -euo pipefail` not found in the script's prologue "
                f"(first {STRICT_MODE_WINDOW} non-blank, non-comment lines). "
                "Without strict mode, silent failures and unset-variable "
                "typos go through unnoticed."
            ),
            recommended_changes=_RECIPE_STRICT_MODE,
        )
    ]


def _scan_header_comment(path: Path, lines: list[str]) -> list[dict]:
    window = lines[1:HEADER_WINDOW]
    comment_count = sum(1 for ln in window if ln.lstrip().startswith("#"))
    if comment_count >= MIN_HEADER_COMMENTS:
        return []
    return [
        emit_json_finding(
            rule_id="header-comment",
            status="warn",
            location={"line": 1, "context": f"{path}: header window"},
            reasoning=(
                f"Fewer than {MIN_HEADER_COMMENTS} comment lines in the "
                "first 10 lines. Without a header block, a reader cannot "
                "see purpose, usage, dependencies, or exit codes."
            ),
            recommended_changes=_RECIPE_HEADER_COMMENT,
        )
    ]


def _scan_main_fn(path: Path, lines: list[str]) -> list[dict]:
    if any(_MAIN_FN_RE.match(ln) for ln in lines):
        return []
    return [
        emit_json_finding(
            rule_id="main-fn",
            status="warn",
            location=None,
            reasoning=(
                "No `main` function defined. A flat top-level script "
                "cannot be sourced for testing without re-running the work."
            ),
            recommended_changes=_RECIPE_MAIN_FN,
        )
    ]


def _scan_main_guard(path: Path, lines: list[str]) -> list[dict]:
    if any(_MAIN_GUARD_RE.search(ln) for ln in lines):
        return []
    return [
        emit_json_finding(
            rule_id="main-guard",
            status="warn",
            location=None,
            reasoning=(
                "Missing BASH_SOURCE-equals-0 sourceable guard. Sourcing "
                "the file (e.g., for testing) will execute main."
            ),
            recommended_changes=_RECIPE_MAIN_GUARD,
        )
    ]


def _scan_readonly_config(path: Path, lines: list[str]) -> list[dict]:
    upper_assigns = sum(1 for ln in lines if _UPPERCASE_ASSIGN_RE.match(ln))
    readonly_decls = sum(1 for ln in lines if _READONLY_DECL_RE.match(ln))
    if not (upper_assigns >= 2 and readonly_decls == 0):
        return []
    return [
        emit_json_finding(
            rule_id="readonly-config",
            status="warn",
            location=None,
            reasoning=(
                f"{upper_assigns} top-level UPPERCASE constants are not "
                "declared `readonly`. Accidental reassignment downstream "
                "will silently change configuration."
            ),
            recommended_changes=_RECIPE_READONLY_CONFIG,
        )
    ]


def _scan_mktemp_trap(path: Path, lines: list[str]) -> list[dict]:
    first_mktemp: int | None = None
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            continue
        if _MKTEMP_RE.search(line):
            first_mktemp = lineno
            break
    if first_mktemp is None:
        return []
    first_trap: int | None = None
    for lineno, line in enumerate(lines, 1):
        if _TRAP_EXIT_RE.search(line):
            first_trap = lineno
            break
    if first_trap is not None and first_trap <= first_mktemp:
        return []
    return [
        emit_json_finding(
            rule_id="mktemp-trap-pairing",
            status="warn",
            location={
                "line": first_mktemp,
                "context": f"{path}: mktemp without preceding trap",
            },
            reasoning=(
                f"`mktemp` at line {first_mktemp} without a preceding "
                "`trap ... EXIT`. set -e exits between mktemp and trap "
                "leave orphaned temp state."
            ),
            recommended_changes=_RECIPE_MKTEMP_TRAP,
        )
    ]


_SCANNERS = {
    "shebang": _scan_shebang,
    "strict-mode": _scan_strict_mode,
    "header-comment": _scan_header_comment,
    "main-fn": _scan_main_fn,
    "main-guard": _scan_main_guard,
    "readonly-config": _scan_readonly_config,
    "mktemp-trap-pairing": _scan_mktemp_trap,
}


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_structure.py: cannot read {path}: {err}", file=sys.stderr)
        return
    for rule_id in _RULE_ORDER:
        per_rule[rule_id].extend(_SCANNERS[rule_id](path, lines))


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_structure.py",
        description="Tier-1 bash structural checker (7 sub-checks).",
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

    per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
    for f in files:
        _scan_file(f, per_rule)

    envelopes = [
        emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in _RULE_ORDER
    ]
    print_envelope(envelopes)
    any_fail = any(e["overall_status"] == "fail" for e in envelopes)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
