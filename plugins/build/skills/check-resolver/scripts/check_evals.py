#!/usr/bin/env python3
"""Tier-1 `.resolver/` trigger-eval sidecar checks — emits JSON ARRAY of two envelopes.

Two rules per target repo root:

- **evals-parse** (FAIL) — ``.resolver/evals.yml`` exists, is parseable, and
  matches the documented schema: top-level ``cases:`` list; each case has a
  non-empty ``prompt`` and at least one of ``expected_filing`` or
  ``expected_context``. Per-case validation errors accumulate as separate
  findings. Multi-target invocation accumulates findings across all targets.
- **eval-pass-stale** (WARN) — ``.resolver/.eval-pass`` mtime older than
  30 days, or the file is absent (never-run).

The YAML parser is a minimal hand-rolled scanner for the documented
schema shape — the toolkit convention is stdlib-only. Files in more
exotic YAML shapes (anchors, flow mappings, multi-line scalars) fail
with a schema-shape FAIL directing the user back to the documented form.

Exit codes:
  0  — overall_status pass / warn / inapplicable for every emitted envelope
  1  — overall_status=fail for any envelope
  64 — usage error

Example:
    ./check_evals.py .
    ./check_evals.py /path/to/repo-a /path/to/repo-b
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

EVALS_RELATIVE = Path(".resolver/evals.yml")
PASS_RELATIVE = Path(".resolver/.eval-pass")
STALE_SECONDS = 30 * 24 * 60 * 60

DOCUMENTED_SCHEMA_HINT = (
    "Expected shape: top-level 'cases:' list; each item has '- prompt: <str>' "
    "and at least one of 'expected_filing: <path>' or 'expected_context: [<paths>]'."
)

_RULE_ORDER: list[str] = ["evals-parse", "eval-pass-stale"]

_RECIPES: dict[str, str] = {
    "evals-parse": (
        "Fix the YAML so it matches the documented schema:\n"
        "    cases:\n"
        "      - prompt: \"save this raw webhook payload\"\n"
        "        expected_filing: .raw/\n"
        "      - prompt: \"where do hook conventions live\"\n"
        "        expected_context:\n"
        "          - plugins/build/_shared/references/hook-best-practices.md\n\n"
        "Each case requires a non-empty `prompt` and at least one of "
        "`expected_filing` or `expected_context`. The most common failures "
        "are unescaped quotes and inconsistent indentation; exotic YAML "
        "(anchors, flow mappings, multi-line scalars) is not supported by "
        "the stdlib parser. If the file is missing, create "
        "`.resolver/evals.yml` via /build:build-resolver (seeds the file "
        "with initial cases). An unparseable or empty eval file is "
        "equivalent to no evals — untested routing is unproven routing."
    ),
    "eval-pass-stale": (
        "Run `/build:check-resolver --run-evals` to execute the cases in "
        "`.resolver/evals.yml`; fix any failing cases (resolver or evals, "
        "depending on which drifted) and the run will refresh "
        "`.resolver/.eval-pass`. The 30-day staleness threshold is "
        "conservative and tunable — the point is that untested routing is "
        "unproven routing."
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


def parse_scalar(value: str) -> str:
    """Strip enclosing quotes and trailing whitespace from a YAML scalar."""
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ('"', "'"):
        return stripped[1:-1]
    return stripped


def parse_inline_list(value: str) -> list[str] | None:
    """Parse ``[a, b, c]`` or ``["a", "b"]`` into a list of scalar strings."""
    stripped = value.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return None
    inner = stripped[1:-1]
    if not inner.strip():
        return []
    return [parse_scalar(part) for part in inner.split(",")]


def parse_field_value(value: str) -> object:
    value = value.strip()
    if not value:
        return ""
    inline = parse_inline_list(value)
    if inline is not None:
        return inline
    return parse_scalar(value)


def parse_cases(text: str) -> list[dict[str, object]] | None:
    """Minimal YAML parser for the documented evals.yml schema."""
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


def check_evals(evals_path: Path, per_rule: dict[str, list[dict]]) -> None:
    if not evals_path.is_file():
        per_rule["evals-parse"].append(
            _make_finding(
                "evals-parse",
                "FAIL",
                f"{evals_path}: evals.yml does not exist",
                "No `.resolver/evals.yml` exists; the resolver has no "
                "regression tests to verify routing decisions stay correct.",
            )
        )
        return
    try:
        text = evals_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"check_evals.py: cannot read {evals_path}: {err}", file=sys.stderr)
        return
    cases = parse_cases(text)
    if cases is None:
        per_rule["evals-parse"].append(
            _make_finding(
                "evals-parse",
                "FAIL",
                f"{evals_path}: schema-shape mismatch",
                f"File does not match the documented schema. "
                f"{DOCUMENTED_SCHEMA_HINT}",
            )
        )
        return
    if not cases:
        per_rule["evals-parse"].append(
            _make_finding(
                "evals-parse",
                "FAIL",
                f"{evals_path}: cases list is empty",
                "evals.yml parses but contains zero cases; a resolver "
                "without evals is a decoration.",
            )
        )
        return
    errors = validate_cases(cases)
    for err in errors:
        per_rule["evals-parse"].append(
            _make_finding(
                "evals-parse",
                "FAIL",
                f"{evals_path}: {err}",
                f"Per-case schema validation failed: {err}. Each case must "
                "have a non-empty 'prompt' and at least one of "
                "'expected_filing' or 'expected_context'.",
            )
        )


def check_eval_pass_stale(
    pass_path: Path, per_rule: dict[str, list[dict]]
) -> None:
    if not pass_path.is_file():
        per_rule["eval-pass-stale"].append(
            _make_finding(
                "eval-pass-stale",
                "WARN",
                f"{pass_path}: {pass_path.name} does not exist",
                "Evals have never been run; routing is unverified.",
            )
        )
        return
    age_seconds = time.time() - pass_path.stat().st_mtime
    if age_seconds > STALE_SECONDS:
        days = int(age_seconds / 86400)
        per_rule["eval-pass-stale"].append(
            _make_finding(
                "eval-pass-stale",
                "WARN",
                f"{pass_path}: last eval-pass is {days} days old (threshold 30)",
                f"`.eval-pass` mtime is {days} days old, beyond the 30-day "
                "freshness threshold; the resolver may have drifted since "
                "the last verified pass.",
            )
        )


def check_repo(repo_root: Path, per_rule: dict[str, list[dict]]) -> None:
    if not repo_root.is_dir():
        print(f"check_evals.py: not a directory: {repo_root}", file=sys.stderr)
        raise _UsageError
    evals_path = repo_root / EVALS_RELATIVE
    pass_path = repo_root / PASS_RELATIVE
    check_evals(evals_path, per_rule)
    check_eval_pass_stale(pass_path, per_rule)


class _UsageError(Exception):
    pass


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_evals.py",
        description=(
            "Tier-1 deterministic checks for .resolver/evals.yml and "
            ".resolver/.eval-pass (JSON envelope output)."
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
