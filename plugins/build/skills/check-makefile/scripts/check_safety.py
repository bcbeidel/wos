#!/usr/bin/env python3
"""Tier-1 Makefile safety checker — emits JSON ARRAY of five envelopes.

Five rules:
  - unguarded-rm   (FAIL): `rm -rf $(VAR)` lacking a non-empty guard,
                           a scoped path (BUILD_DIR, BUILD_ROOT, OUT_DIR,
                           DIST_DIR, TARGET_DIR), or `--`.
  - sudo           (FAIL): `sudo` invocation in a recipe.
  - global-install (FAIL): `npm install -g`, unscoped `pip install`,
                           `gem install` without `--user-install`.
  - curl-pipe      (FAIL): pipe-to-shell pattern (curl piped into sh/bash).
  - destructive-guard (WARN): targets named `deploy`, `publish`, `release`,
                              or `prod-*` must begin their recipe with a
                              confirmation-variable guard (CONFIRM /
                              CONFIRMED / YES / I_REALLY_MEAN_IT).

Exit codes:
  0  — overall_status pass / warn for every emitted envelope
  1  — overall_status=fail for any envelope
  64 — usage error

Example:
    ./check_safety.py path/to/Makefile path/to/mk/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
PROG = "check_safety.py"

_TARGET_RE = re.compile(r"^([A-Za-z0-9_./$()%-]+)\s*:(?!=)")

_RM_RF_RE = re.compile(r"\brm\s+-[rR][fF]?\s+(\S+)")
_SUDO_RE = re.compile(r"(?:^|[\s;|&])sudo\b")
_NPM_G_RE = re.compile(r"\bnpm\s+install[^\n]*\s-g\b|\bnpm\s+i[^\n]*\s-g\b")
_PIP_GLOBAL_RE = re.compile(
    r"\bpip(?:3)?\s+install\b(?!(?:[^\n]*--user|[^\n]*--target|[^\n]*--prefix|[^\n]*-e\s+\.?\S*))"
)
_GEM_GLOBAL_RE = re.compile(r"\bgem\s+install\b(?![^\n]*--user-install)")
_CURL_PIPE_RE = re.compile(r"\bcurl\b[^\n]*\|\s*(?:sudo\s+)?(?:sh|bash)\b")

_SAFE_PATH_HINTS = ("BUILD_DIR", "BUILD_ROOT", "OUT_DIR", "DIST_DIR", "TARGET_DIR")
_DESTRUCTIVE_NAMES = ("deploy", "publish", "release")
_CONFIRM_VARS_RE = re.compile(r"\b(CONFIRM|CONFIRMED|YES|I_REALLY_MEAN_IT)\b")

_RECIPE_UNGUARDED_RM = (
    "Guard `rm -rf $(VAR)` with a non-empty check, scope it to a known "
    "build directory (`$(BUILD_DIR)`, `$(OUT_DIR)`, `$(DIST_DIR)`), or "
    "include `--` before the argument so an empty/unset VAR cannot expand "
    "into `rm -rf /`.\n\n"
    "Example:\n"
    "    clean: ## Remove build artifacts.\n"
    "    \t@[[ -n \"$(BUILD_DIR)\" && \"$(BUILD_DIR)\" != \"/\" ]] || "
    "{ echo \"BUILD_DIR misconfigured\" >&2; exit 1; }\n"
    "    \trm -rf -- \"$(BUILD_DIR)\"\n"
)

_RECIPE_SUDO = (
    "Remove `sudo` from the recipe. Dev workflows must not mutate the "
    "user's machine — install into user-local paths instead "
    "(`pip install --user`, `npm install --save-dev`, a `.venv/`, "
    "`./node_modules/`).\n\n"
    "Example:\n"
    "    install:\n"
    "    \tpip install --user -e .   # or use .venv/bin/pip\n"
)

_RECIPE_GLOBAL_INSTALL = (
    "Install into a project-local location, not a global prefix.\n"
    "  - npm: `npm install --save-dev <pkg>` (writes to ./node_modules)\n"
    "  - pip: `pip install --user <pkg>` or use a venv "
    "(`.venv/bin/pip install -e .`)\n"
    "  - gem: `gem install --user-install <pkg>` or pin to a Gemfile.\n\n"
    "Global installs drift between developer machines and CI, producing "
    "'works on my laptop' bugs."
)

_RECIPE_CURL_PIPE = (
    "Replace `curl ... | sh|bash` with a versioned, checksummed install: "
    "download to a fixed path, verify with `sha256sum -c -`, then execute.\n\n"
    "Example:\n"
    "    setup:\n"
    "    \t@curl -fsSL -o /tmp/install.sh https://example.com/install-v1.2.3.sh\n"
    "    \t@echo \"abc123...  /tmp/install.sh\" | sha256sum -c -\n"
    "    \t@bash /tmp/install.sh\n\n"
    "Piped-remote-install is the classic supply-chain footgun — "
    "whoever controls the URL today controls your dev machine tomorrow."
)

_RECIPE_DESTRUCTIVE_GUARD = (
    "Make the first recipe command a `CONFIRM=1` guard so an accidental "
    "`make deploy` is a no-op rather than a production incident.\n\n"
    "Example:\n"
    "    deploy: ## Deploy to production (set CONFIRM=1).\n"
    "    \t@[[ \"$${CONFIRM:-0}\" = \"1\" ]] || "
    "{ echo \"set CONFIRM=1 to deploy\" >&2; exit 1; }\n"
    "    \t./scripts/deploy.sh production\n"
)


_RULE_ORDER = [
    "unguarded-rm",
    "sudo",
    "global-install",
    "curl-pipe",
    "destructive-guard",
]


class _UsageError(Exception):
    pass


def _is_makefile(path: Path) -> bool:
    return path.name in ("Makefile", "GNUmakefile") or path.suffix == ".mk"


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_makefile(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_makefile(child):
                    files.append(child)
        else:
            print(f"{PROG}: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _rm_is_guarded(lines: list[str], idx: int, operand: str) -> bool:
    # Scoped path literal or known-safe variable name.
    if "--" in lines[idx]:
        return True
    if any(hint in operand for hint in _SAFE_PATH_HINTS):
        return True
    # Preceding recipe line (within ~3 lines) has a non-empty check.
    for back in range(1, 4):
        if idx - back < 0:
            break
        prev = lines[idx - back]
        if not prev.startswith("\t"):
            break
        if "-n " in prev or "-z " in prev or "exit 1" in prev or "|| exit" in prev:
            return True
    return False


def _is_destructive_name(name: str) -> bool:
    if name in _DESTRUCTIVE_NAMES:
        return True
    return name.startswith("prod-") or name.startswith("prod_")


def _recipe_first_line(lines: list[str], target_idx: int) -> str | None:
    for i in range(target_idx + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        if line.startswith("\t"):
            return line
        return None
    return None


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"{PROG}: cannot read {path}: {err}", file=sys.stderr)
        return

    # Recipe-line scans (tab-indented).
    for idx, line in enumerate(lines):
        if not line.startswith("\t"):
            continue
        lineno = idx + 1
        ctx = f"{path}: {line.strip()[:80]}"

        rm_match = _RM_RF_RE.search(line)
        if rm_match and not _rm_is_guarded(lines, idx, rm_match.group(1)):
            per_rule["unguarded-rm"].append(
                emit_json_finding(
                    rule_id="unguarded-rm",
                    status="fail",
                    location={"line": lineno, "context": ctx},
                    reasoning=(
                        f"line {lineno} runs `rm -rf` without a non-empty "
                        "guard, a scoped build-directory variable, or `--`. "
                        "If the variable expands empty, `rm -rf` becomes "
                        "`rm -rf /` — one typo from disaster."
                    ),
                    recommended_changes=_RECIPE_UNGUARDED_RM,
                )
            )

        if _SUDO_RE.search(line):
            per_rule["sudo"].append(
                emit_json_finding(
                    rule_id="sudo",
                    status="fail",
                    location={"line": lineno, "context": ctx},
                    reasoning=(
                        f"line {lineno} invokes `sudo`. Dev workflows must "
                        "not mutate the user's machine; install into "
                        "user-local paths instead."
                    ),
                    recommended_changes=_RECIPE_SUDO,
                )
            )

        if _NPM_G_RE.search(line):
            per_rule["global-install"].append(
                emit_json_finding(
                    rule_id="global-install",
                    status="fail",
                    location={"line": lineno, "context": f"{path}: npm install -g"},
                    reasoning=(
                        f"line {lineno} runs `npm install -g`. Global "
                        "installs drift between machines; install into "
                        "`./node_modules/` instead."
                    ),
                    recommended_changes=_RECIPE_GLOBAL_INSTALL,
                )
            )

        if _PIP_GLOBAL_RE.search(line):
            per_rule["global-install"].append(
                emit_json_finding(
                    rule_id="global-install",
                    status="fail",
                    location={
                        "line": lineno,
                        "context": f"{path}: unscoped pip install",
                    },
                    reasoning=(
                        f"line {lineno} runs `pip install` without `--user`, "
                        "`--target`, `--prefix`, or `-e .`. Without a venv "
                        "or scoped install, this writes to the system Python."
                    ),
                    recommended_changes=_RECIPE_GLOBAL_INSTALL,
                )
            )

        if _GEM_GLOBAL_RE.search(line):
            per_rule["global-install"].append(
                emit_json_finding(
                    rule_id="global-install",
                    status="fail",
                    location={
                        "line": lineno,
                        "context": f"{path}: gem install (no --user-install)",
                    },
                    reasoning=(
                        f"line {lineno} runs `gem install` without "
                        "`--user-install`. Global gems drift across machines."
                    ),
                    recommended_changes=_RECIPE_GLOBAL_INSTALL,
                )
            )

        if _CURL_PIPE_RE.search(line):
            per_rule["curl-pipe"].append(
                emit_json_finding(
                    rule_id="curl-pipe",
                    status="fail",
                    location={"line": lineno, "context": ctx},
                    reasoning=(
                        f"line {lineno} pipes `curl` output into a shell. "
                        "Whoever controls that URL today controls your dev "
                        "machine tomorrow."
                    ),
                    recommended_changes=_RECIPE_CURL_PIPE,
                )
            )

    # Destructive-guard scan (target-line scope).
    for idx, line in enumerate(lines):
        if line.startswith("\t"):
            continue
        match = _TARGET_RE.match(line)
        if not match:
            continue
        name = match.group(1)
        if not _is_destructive_name(name):
            continue
        first = _recipe_first_line(lines, idx)
        if not first or not _CONFIRM_VARS_RE.search(first):
            per_rule["destructive-guard"].append(
                emit_json_finding(
                    rule_id="destructive-guard",
                    status="warn",
                    location={
                        "line": idx + 1,
                        "context": f"{path}: target `{name}` lacks confirmation guard",
                    },
                    reasoning=(
                        f"target `{name}` at line {idx + 1} is destructive "
                        "by name (deploy/publish/release/prod-*) but its "
                        "first recipe command is not a CONFIRM/YES guard. "
                        "Accidental `make {name}` runs the command."
                    ).replace("{name}", name),
                    recommended_changes=_RECIPE_DESTRUCTIVE_GUARD,
                )
            )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Tier-1 Makefile safety checker (unguarded rm, sudo, "
            "global install, curl-pipe, destructive-guard)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more Makefile / *.mk files or directories (non-recursive).",
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
