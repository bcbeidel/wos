#!/usr/bin/env python3
"""Tier-1 prose pre-check for Claude Code rule files.

Emits a JSON ARRAY of three envelopes per `_common.py`. All findings emit
at WARN severity — these are heuristics with legitimate exceptions (e.g.,
"Never log PII" is a valid prohibition-only rule). Tier-2 remains the
judgment layer; WARN does not exit non-zero.

- `hedge` (WARN): hedged phrasing (`prefer`, `generally`, `usually`,
  `consider`, `where appropriate`, `as appropriate`,
  `where it makes sense`).
- `prohibition-opener` (WARN): rule statement opens with `Don't` /
  `Never` / `Avoid` (heuristic — keep the WARN as-is when the negation
  is load-bearing).
- `synthetic-placeholder` (WARN): synthetic identifiers inside fenced
  code blocks (`foo`+`bar`, `myFunction`/`myClass`/...,
  `Widget`/`SomeClass`, `placeholder`, `example_*`).

Exit codes:
  0  — overall_status pass / warn / inapplicable for every envelope
  1  — overall_status=fail (not produced by this script)
  64 — usage error

Example:
    ./check_prose.py .claude/rules/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

HEDGE_WORD_RE = re.compile(r"\b(prefer|generally|usually|consider)\b", re.IGNORECASE)
HEDGE_PHRASE_RE = re.compile(
    r"\b(where appropriate|as appropriate|where it makes sense)\b",
    re.IGNORECASE,
)
PROHIBITION_RE = re.compile(r"^(Don'?t|Never|Avoid)(\s|$)")
MARKDOWN_PREFIX_RE = re.compile(r"^(\s*(#+|[*-]|>|\*\*)\s*)+")

FOO_RE = re.compile(r"(?<![A-Za-z_])foo(?![A-Za-z_])", re.IGNORECASE)
BAR_RE = re.compile(r"(?<![A-Za-z_])bar(?![A-Za-z_])", re.IGNORECASE)
MY_IDENT_RE = re.compile(
    r"(?<![A-Za-z_])(myFunction|myClass|myObject|myVariable|myComponent)(?![A-Za-z_])"
)
GENERIC_CLASS_RE = re.compile(
    r"(?<![A-Za-z_])(Widget|MyWidget|SomeClass|SomeThing)(?![A-Za-z_])"
)
PLACEHOLDER_RE = re.compile(
    r"(?<![A-Za-z_])(placeholder|example_[A-Za-z_]+)(?![A-Za-z_])"
)

_RULE_ORDER: list[str] = ["hedge", "prohibition-opener", "synthetic-placeholder"]

_RECIPE_HEDGE = (
    "Commit to the directive; move the hedge into a named exception if "
    "one exists. Hedged rules push judgment back onto Claude at every "
    "invocation, defeating the point of writing the rule down.\n\n"
    "Example:\n"
    "    Generally prefer composition over inheritance.\n"
    "      -> Use composition over inheritance. Exception: when extending\n"
    "         a framework base class that requires inheritance (e.g.,\n"
    "         `React.Component` in legacy code).\n"
)

_RECIPE_PROHIBITION_OPENER = (
    "Restate as a positive action, or pair the prohibition with its "
    "positive alternative. Negations are fragile — a dropped or "
    "misattributed `not`/`don't`/`never` inverts the rule. If the "
    "negation is load-bearing (no clean positive counterpart, e.g., "
    '"Never log PII"), the WARN is a false positive and the rule can '
    "stay as-is.\n\n"
    "Example:\n"
    "    Don't use global state.\n"
    "      -> Thread dependencies through constructors; never reach for\n"
    "         module-level globals.\n"
)

_RECIPE_SYNTHETIC_PLACEHOLDER = (
    "Replace synthetic identifiers (`foo`, `bar`, `myFunction`, `Widget`, "
    "`placeholder`, `example_*`) with real code from the codebase — actual "
    "table names, function names, module paths. Domain-specific identifiers "
    "anchor the rule more strongly; a file-path comment (optional) "
    "strengthens provenance.\n\n"
    "Example:\n"
    "    function foo(x) { return bar(x); }\n"
    "      -> // src/api/handlers/users.ts\n"
    "         async function getUser(userId: string) {\n"
    "           return db.users.findById(userId);\n"
    "         }\n"
)

_RECIPES: dict[str, str] = {
    "hedge": _RECIPE_HEDGE,
    "prohibition-opener": _RECIPE_PROHIBITION_OPENER,
    "synthetic-placeholder": _RECIPE_SYNTHETIC_PLACEHOLDER,
}


def _make_finding(
    rule_id: str, path: Path, line_no: int, context: str, reasoning: str
) -> dict:
    return emit_json_finding(
        rule_id=rule_id,
        status="warn",
        location={"line": line_no, "context": f"{path}: {context}"},
        reasoning=reasoning,
        recommended_changes=_RECIPES[rule_id],
    )


def frontmatter_bounds(lines: list[str]) -> tuple[int, int]:
    """Return (start, end_exclusive) indices of the frontmatter block, or (0, 0)."""
    if not lines or lines[0].rstrip("\n") != "---":
        return (0, 0)
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            return (0, i + 1)
    return (0, 0)


def scan_code_line(
    path: Path, line_no: int, line: str, per_rule: dict[str, list[dict]]
) -> None:
    if FOO_RE.search(line) and BAR_RE.search(line):
        per_rule["synthetic-placeholder"].append(
            _make_finding(
                "synthetic-placeholder",
                path,
                line_no,
                "synthetic identifier (foo/bar) in code example",
                f"line {line_no} uses `foo`/`bar` placeholders in a code "
                "example. Synthetic identifiers weaken example anchoring.",
            )
        )
    if MY_IDENT_RE.search(line):
        per_rule["synthetic-placeholder"].append(
            _make_finding(
                "synthetic-placeholder",
                path,
                line_no,
                "placeholder identifier (my*) in code example",
                f"line {line_no} uses a `my*` placeholder in a code "
                "example. Replace with a real identifier from the codebase.",
            )
        )
    if GENERIC_CLASS_RE.search(line):
        per_rule["synthetic-placeholder"].append(
            _make_finding(
                "synthetic-placeholder",
                path,
                line_no,
                "placeholder class (Widget/SomeClass) in code example",
                f"line {line_no} uses a generic class placeholder "
                "(Widget/SomeClass). Replace with a real class.",
            )
        )
    if PLACEHOLDER_RE.search(line):
        per_rule["synthetic-placeholder"].append(
            _make_finding(
                "synthetic-placeholder",
                path,
                line_no,
                "placeholder token in code example",
                f"line {line_no} contains a `placeholder`/`example_*` "
                "token. Replace with a real identifier.",
            )
        )


def scan_prose_line(
    path: Path, line_no: int, line: str, per_rule: dict[str, list[dict]]
) -> None:
    hedge = HEDGE_WORD_RE.search(line)
    if hedge:
        word = hedge.group(1).lower()
        per_rule["hedge"].append(
            _make_finding(
                "hedge",
                path,
                line_no,
                f'hedged word "{word}"',
                f'line {line_no} uses hedged phrasing "{word}". Hedges '
                "push judgment back onto Claude at every invocation.",
            )
        )
    if HEDGE_PHRASE_RE.search(line):
        per_rule["hedge"].append(
            _make_finding(
                "hedge",
                path,
                line_no,
                "hedged phrase",
                f"line {line_no} uses a hedged phrase "
                "(`where appropriate` / `as appropriate` / "
                "`where it makes sense`). Replace with a specific "
                "condition or remove the hedge.",
            )
        )

    stripped = MARKDOWN_PREFIX_RE.sub("", line)
    opener = PROHIBITION_RE.match(stripped)
    if opener:
        word = opener.group(1)
        per_rule["prohibition-opener"].append(
            _make_finding(
                "prohibition-opener",
                path,
                line_no,
                f'prohibition opener "{word}"',
                f'line {line_no} opens with "{word}". Negations are '
                "fragile; a dropped `not`/`don't`/`never` inverts the rule.",
            )
        )


def scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"warn: cannot read {path}: {err}", file=sys.stderr)
        return

    lines = text.splitlines()
    _, fm_end = frontmatter_bounds([line + "\n" for line in lines])

    in_code = False
    for idx, line in enumerate(lines, start=1):
        if idx <= fm_end:
            continue
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            scan_code_line(path, idx, line, per_rule)
        else:
            scan_prose_line(path, idx, line, per_rule)


def iter_targets(targets: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    for target in targets:
        if target.is_file():
            resolved.append(target)
        elif target.is_dir():
            resolved.extend(sorted(target.rglob("*.md")))
        else:
            print(f"error: path not found: {target}", file=sys.stderr)
            raise SystemExit(EXIT_USAGE)
    return resolved


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prose pre-check for Claude Code rule files (WARN only).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Rule files or directories to scan (directories walked for *.md).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        for file_path in iter_targets(args.paths):
            scan_file(file_path, per_rule)
        envelopes = [
            emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in _RULE_ORDER
        ]
        print_envelope(envelopes)
        any_fail = any(e["overall_status"] == "fail" for e in envelopes)
        return 1 if any_fail else 0
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
