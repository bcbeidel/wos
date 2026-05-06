#!/usr/bin/env python3
"""Tier-1 AGENTS.md → RESOLVER.md pointer checks — emits JSON ARRAY of two envelopes.

Two rules per target repo root:

- **pointer-present** (FAIL) — AGENTS.md exists at the repo root and contains
  a literal reference to ``RESOLVER.md``. Absence of AGENTS.md itself emits
  under this rule (there is nothing to anchor from).
- **pointer-resolves** (FAIL) — the RESOLVER.md the pointer names exists on
  disk relative to the repo root. Skipped (no findings emitted) when
  pointer-present already failed for the same target.

Multi-target invocation: each target is one repo root; findings accumulate
across targets, then one envelope per rule_id is emitted.

Exit codes:
  0  — overall_status pass / warn / inapplicable for every emitted envelope
  1  — overall_status=fail for any envelope
  64 — usage error

Example:
    ./check_pointer.py .
    ./check_pointer.py /path/to/repo-a /path/to/repo-b
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

POINTER_MARKER = "RESOLVER.md"
AGENTS_FILENAME = "AGENTS.md"
RESOLVER_FILENAME = "RESOLVER.md"

_RULE_ORDER: list[str] = ["pointer-present", "pointer-resolves"]

_RECIPES: dict[str, str] = {
    "pointer-present": (
        "Add a one-line pointer to AGENTS.md, typically inserted after the "
        "first major section (commonly 'Context Navigation'):\n\n"
        "    Before filing new content or loading context beyond a skill's "
        "eager `references:`, consult `RESOLVER.md`.\n\n"
        "If AGENTS.md does not yet exist, create it at the repo root with "
        "this pointer. Without the AGENTS.md anchor, the resolver is "
        "unreachable from the root of the context — a file no session opens."
    ),
    "pointer-resolves": (
        "Either correct the AGENTS.md pointer to RESOLVER.md's actual "
        "location, or move RESOLVER.md to where the pointer expects it. "
        "Example: if the pointer names `docs/RESOLVER.md` but the file lives "
        "at `./RESOLVER.md`, update the pointer to `./RESOLVER.md` (or move "
        "the file to `docs/RESOLVER.md`). A dangling pointer is the worst "
        "outcome — the surface says the resolver is reachable while it "
        "silently isn't."
    ),
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
        status="fail" if severity == "FAIL" else "warn",
        location={"line": line, "context": location_context},
        reasoning=reasoning,
        recommended_changes=_RECIPES[rule_id],
    )


def check_pointer_present(
    agents_path: Path, per_rule: dict[str, list[dict]]
) -> bool:
    if not agents_path.is_file():
        per_rule["pointer-present"].append(
            _make_finding(
                "pointer-present",
                "FAIL",
                f"{agents_path}: {AGENTS_FILENAME} does not exist at repo root",
                f"{AGENTS_FILENAME} is missing — the entry point for the "
                "resolver pointer cannot anchor from a file that does not exist.",
            )
        )
        return False
    try:
        text = agents_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"check_pointer.py: cannot read {agents_path}: {err}", file=sys.stderr)
        return False
    if POINTER_MARKER not in text:
        per_rule["pointer-present"].append(
            _make_finding(
                "pointer-present",
                "FAIL",
                f"{agents_path}: {AGENTS_FILENAME} does not reference {POINTER_MARKER}",
                f"{AGENTS_FILENAME} exists but contains no reference to "
                f"{POINTER_MARKER}; sessions never see the routing table.",
            )
        )
        return False
    return True


def check_pointer_resolves(
    repo_root: Path, per_rule: dict[str, list[dict]]
) -> bool:
    resolver_path = repo_root / RESOLVER_FILENAME
    if not resolver_path.is_file():
        per_rule["pointer-resolves"].append(
            _make_finding(
                "pointer-resolves",
                "FAIL",
                f"{repo_root / AGENTS_FILENAME}: pointer names "
                f"{POINTER_MARKER} but {resolver_path} does not exist",
                f"AGENTS.md references {POINTER_MARKER} but the file is "
                "absent from disk; the pointer is dangling.",
            )
        )
        return False
    return True


def check_repo(repo_root: Path, per_rule: dict[str, list[dict]]) -> None:
    if not repo_root.is_dir():
        print(f"check_pointer.py: not a directory: {repo_root}", file=sys.stderr)
        raise _UsageError
    agents_path = repo_root / AGENTS_FILENAME
    if not check_pointer_present(agents_path, per_rule):
        # Preserve early-return: skip pointer-resolves when pointer-present failed.
        return
    check_pointer_resolves(repo_root, per_rule)


class _UsageError(Exception):
    pass


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_pointer.py",
        description=(
            "Tier-1 deterministic checks for the AGENTS.md → RESOLVER.md "
            "pointer (JSON envelope output)."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="One or more repo-root paths (defaults to current directory).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
    try:
        for repo_root in args.paths:
            check_repo(repo_root, per_rule)
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED

    envelopes = [
        emit_rule_envelope(rule_id=rid, findings=per_rule[rid]) for rid in _RULE_ORDER
    ]
    print_envelope(envelopes)
    any_fail = any(env["overall_status"] == "fail" for env in envelopes)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
