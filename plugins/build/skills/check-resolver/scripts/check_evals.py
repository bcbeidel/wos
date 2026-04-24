#!/usr/bin/env python3
"""Deterministic Tier-1 checks for the `.resolver/` trigger-eval sidecar.

Two checks per target repo root:

- **evals-parse** — ``.resolver/evals.yml`` is valid YAML matching the
  documented schema: top-level ``cases:`` list; each case has a
  non-empty ``prompt`` and at least one of ``expected_filing`` or
  ``expected_context``. FAIL otherwise.
- **eval-pass-stale** — ``.resolver/.eval-pass`` mtime older than
  30 days, or the file is absent (never-run). WARN.

The YAML parser is a minimal hand-rolled scanner for the documented
schema shape — the toolkit convention is stdlib-only. Files in more
exotic YAML shapes (anchors, flow mappings, multi-line scalars) fail
with a schema-shape FAIL directing the user back to the documented
form.

Example:
    ./check_evals.py .
    ./check_evals.py /path/to/repo-a /path/to/repo-b
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

EXIT_USAGE = 2
EXIT_INTERRUPTED = 130

EVALS_RELATIVE = Path(".resolver/evals.yml")
PASS_RELATIVE = Path(".resolver/.eval-pass")
STALE_SECONDS = 30 * 24 * 60 * 60

DOCUMENTED_SCHEMA_HINT = (
    "Expected shape: top-level 'cases:' list; each item has '- prompt: <str>' "
    "and at least one of 'expected_filing: <path>' or 'expected_context: [<paths>]'."
)


def emit_fail(path: Path, check: str, detail: str, recommendation: str) -> None:
    print(f"FAIL  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def emit_warn(path: Path, check: str, detail: str, recommendation: str) -> None:
    print(f"WARN  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def parse_scalar(value: str) -> str:
    """Strip enclosing quotes and trailing whitespace from a YAML scalar."""
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ('"', "'"):
        return stripped[1:-1]
    return stripped


def parse_inline_list(value: str) -> list[str] | None:
    """Parse ``[a, b, c]`` or ``["a", "b"]`` into a list of scalar strings.

    Returns None when ``value`` is not a bracketed inline list.
    """
    stripped = value.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return None
    inner = stripped[1:-1]
    if not inner.strip():
        return []
    return [parse_scalar(part) for part in inner.split(",")]


def parse_cases(text: str) -> list[dict[str, object]] | None:
    """Minimal YAML parser for the documented evals.yml schema.

    Returns a list of case dicts, or None when the file's shape cannot
    be parsed. Caller emits a schema-shape FAIL on None.
    """
    lines = text.splitlines()
    cases: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_cases_block = False

    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == 0:
            if stripped == "cases:":
                in_cases_block = True
                continue
            return None

        if not in_cases_block:
            return None

        if stripped.startswith("- "):
            if current is not None:
                cases.append(current)
            current = {}
            item = stripped[2:].strip()
            if ":" not in item:
                return None
            key, _, value = item.partition(":")
            current[key.strip()] = parse_field_value(value)
            continue

        if current is None:
            return None
        if ":" not in stripped:
            return None
        key, _, value = stripped.partition(":")
        current[key.strip()] = parse_field_value(value)

    if current is not None:
        cases.append(current)
    return cases


def parse_field_value(value: str) -> object:
    value = value.strip()
    if not value:
        return ""
    inline = parse_inline_list(value)
    if inline is not None:
        return inline
    return parse_scalar(value)


def validate_cases(cases: list[dict[str, object]]) -> list[str]:
    """Return a list of per-case error messages; empty list when schema-valid."""
    errors: list[str] = []
    for idx, case in enumerate(cases, start=1):
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"case {idx}: missing or empty 'prompt'")
            continue
        has_filing = bool(case.get("expected_filing"))
        has_context = bool(case.get("expected_context"))
        if not has_filing and not has_context:
            errors.append(
                f"case {idx} ('{prompt}'): missing both 'expected_filing' "
                "and 'expected_context'"
            )
    return errors


def check_evals(evals_path: Path) -> bool:
    if not evals_path.is_file():
        emit_fail(
            evals_path,
            "evals-parse",
            "evals.yml does not exist",
            "Create .resolver/evals.yml via /build:build-resolver "
            "(seeds the file with initial cases)",
        )
        return False
    try:
        text = evals_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"error: cannot read {evals_path}: {err}", file=sys.stderr)
        return False
    cases = parse_cases(text)
    if cases is None:
        emit_fail(
            evals_path,
            "evals-parse",
            f"file does not match documented schema. {DOCUMENTED_SCHEMA_HINT}",
            "Simplify the file to the documented schema; exotic YAML "
            "features (anchors, flow mappings, multi-line scalars) are not supported",
        )
        return False
    if not cases:
        emit_fail(
            evals_path,
            "evals-parse",
            "cases list is empty",
            "Seed at least 1 eval case — a resolver without evals is a decoration",
        )
        return False
    errors = validate_cases(cases)
    if errors:
        for err in errors:
            emit_fail(
                evals_path,
                "evals-parse",
                err,
                "Ensure each case has a non-empty 'prompt' and at least one of "
                "'expected_filing' or 'expected_context'",
            )
        return False
    return True


def check_eval_pass_stale(pass_path: Path) -> None:
    if not pass_path.is_file():
        emit_warn(
            pass_path,
            "eval-pass-stale",
            f"{pass_path.name} does not exist (evals have never been run)",
            "Run /build:check-resolver --run-evals to execute cases and "
            "record a pass timestamp",
        )
        return
    age_seconds = time.time() - pass_path.stat().st_mtime
    if age_seconds > STALE_SECONDS:
        days = int(age_seconds / 86400)
        emit_warn(
            pass_path,
            "eval-pass-stale",
            f"last eval-pass is {days} days old (threshold 30)",
            "Run /build:check-resolver --run-evals to re-verify routing",
        )


def check_repo(repo_root: Path) -> bool:
    if not repo_root.is_dir():
        print(f"error: not a directory: {repo_root}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    evals_path = repo_root / EVALS_RELATIVE
    pass_path = repo_root / PASS_RELATIVE
    ok = check_evals(evals_path)
    check_eval_pass_stale(pass_path)
    return ok


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Tier-1 deterministic checks for .resolver/evals.yml and "
            ".resolver/.eval-pass."
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
    try:
        all_ok = True
        for repo_root in args.paths:
            if not check_repo(repo_root):
                all_ok = False
        return 0 if all_ok else 1
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
