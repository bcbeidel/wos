#!/usr/bin/env python3
"""Tier-1 structural checker for Claude Code rule files.

Emits a JSON ARRAY of three envelopes per `_common.py`:

- `location` (FAIL): file must live under ``.claude/rules/`` (project) or
  ``~/.claude/rules/`` (user).
- `extension` (FAIL): file must end in ``.md`` with no inner extension
  segment. ``.mdx`` / ``.markdown`` / double extensions FAIL.
- `frontmatter-shape` (WARN): only ``paths:`` is a documented top-level
  key; other top-level keys WARN (non-failing).

Exit codes:
  0  — overall_status pass / warn / inapplicable for every envelope
  1  — overall_status=fail for any envelope
  64 — usage error

Example:
    ./check_structure.py .claude/rules/
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

TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):")
DOCUMENTED_KEYS = frozenset({"paths"})

SCAN_EXTENSIONS = {".md", ".mdx", ".markdown"}

_RULE_ORDER: list[str] = ["location", "extension", "frontmatter-shape"]

_RECIPE_LOCATION = (
    "Move the file under `.claude/rules/` (or `~/.claude/rules/` for "
    "user-scope rules). Claude Code only auto-loads rules from those two "
    "directories — files at other paths (e.g., `docs/rules/`, project "
    "root, `rules/` without `.claude/` prefix) are inert and never read.\n\n"
    "Example:\n"
    "    docs/rules/api-handlers.md\n"
    "      -> .claude/rules/api-handlers.md\n"
)

_RECIPE_EXTENSION = (
    "Rename the file to use a single `.md` extension. Claude Code's rule "
    "discovery scans for `.md` files only — `.mdx`, `.markdown`, "
    "`.rule.md`, and other extensions are skipped.\n\n"
    "Example:\n"
    "    .claude/rules/api-handlers.rule.md\n"
    "      -> .claude/rules/api-handlers.md\n"
)

_RECIPE_FRONTMATTER_SHAPE = (
    "Remove unknown top-level frontmatter keys, or move their content "
    "into the body. Claude Code documents only `paths:` in rule "
    "frontmatter; other keys (`severity:`, `description:`, `name:`, "
    "`type:`) are not consumed and add maintenance noise without "
    "behavioral effect.\n\n"
    "Example:\n"
    "    ---\n"
    "    paths:\n"
    '      - "src/api/**/*.ts"\n'
    "    severity: warn        # not consumed — remove\n"
    "    description: ...      # not consumed — move to body\n"
    "    ---\n"
)

_RECIPES: dict[str, str] = {
    "location": _RECIPE_LOCATION,
    "extension": _RECIPE_EXTENSION,
    "frontmatter-shape": _RECIPE_FRONTMATTER_SHAPE,
}


def _make_finding(
    rule_id: str,
    status: str,
    path: Path,
    line: int | None,
    context: str,
    reasoning: str,
) -> dict:
    location = (
        {"line": line, "context": f"{path}: {context}"}
        if line is not None
        else {"line": 1, "context": f"{path}: {context}"}
    )
    return emit_json_finding(
        rule_id=rule_id,
        status=status,
        location=location,
        reasoning=reasoning,
        recommended_changes=_RECIPES[rule_id],
    )


def check_location(path: Path, per_rule: dict[str, list[dict]]) -> None:
    absolute = path.resolve()
    parts = absolute.parts
    for i in range(len(parts) - 1):
        if parts[i] == ".claude" and parts[i + 1] == "rules":
            return
    per_rule["location"].append(
        _make_finding(
            rule_id="location",
            status="fail",
            path=path,
            line=1,
            context="file not under .claude/rules/",
            reasoning=(
                f"{path} is not under `.claude/rules/` or `~/.claude/rules/`. "
                "Claude Code only auto-loads rules from those directories; "
                "this file is inert as-placed."
            ),
        )
    )


def check_extension(path: Path, per_rule: dict[str, list[dict]]) -> None:
    name = path.name
    if name.endswith(".mdx") or name.endswith(".markdown"):
        ext = name.rsplit(".", 1)[1]
        per_rule["extension"].append(
            _make_finding(
                rule_id="extension",
                status="fail",
                path=path,
                line=1,
                context=f"file extension is .{ext}, expected .md",
                reasoning=(
                    f"{path} uses .{ext}. Claude Code's rule discovery scans "
                    "for `.md` files only; this extension is skipped."
                ),
            )
        )
        return
    if not name.endswith(".md"):
        per_rule["extension"].append(
            _make_finding(
                rule_id="extension",
                status="fail",
                path=path,
                line=1,
                context="file has no .md extension",
                reasoning=(
                    f"{path} has no .md extension. Claude Code's rule "
                    "discovery scans for `.md` files only."
                ),
            )
        )
        return
    stem = name[: -len(".md")]
    if "." in stem:
        inner = stem.rsplit(".", 1)[1]
        per_rule["extension"].append(
            _make_finding(
                rule_id="extension",
                status="fail",
                path=path,
                line=1,
                context=f"double extension .{inner}.md",
                reasoning=(
                    f"{path} has a double extension (.{inner}.md). Rule "
                    "discovery treats this as a non-.md file and skips it."
                ),
            )
        )


def check_frontmatter_shape(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"warn: cannot read {path}: {err}", file=sys.stderr)
        return

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return

    for idx in range(1, len(lines)):
        if lines[idx] == "---":
            return
        match = TOP_LEVEL_KEY_RE.match(lines[idx])
        if match and match.group(1) not in DOCUMENTED_KEYS:
            key = match.group(1)
            per_rule["frontmatter-shape"].append(
                _make_finding(
                    rule_id="frontmatter-shape",
                    status="warn",
                    path=path,
                    line=idx + 1,
                    context=f"unknown top-level key '{key}'",
                    reasoning=(
                        f"line {idx + 1} declares unknown top-level key "
                        f"'{key}'. Claude Code documents only `paths:` in "
                        "rule frontmatter; other keys are not consumed."
                    ),
                )
            )


def check_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    check_location(path, per_rule)
    check_extension(path, per_rule)
    check_frontmatter_shape(path, per_rule)


def iter_targets(targets: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    for target in targets:
        if target.is_file():
            resolved.append(target)
        elif target.is_dir():
            matched: list[Path] = []
            for ext in SCAN_EXTENSIONS:
                matched.extend(target.rglob(f"*{ext}"))
            resolved.extend(sorted(set(matched)))
        else:
            print(f"error: path not found: {target}", file=sys.stderr)
            raise SystemExit(EXIT_USAGE)
    return resolved


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Structural checks for Claude Code rule files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help=(
            "Rule files or directories to scan "
            "(directories walked for *.md / *.mdx / *.markdown)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        for file_path in iter_targets(args.paths):
            check_file(file_path, per_rule)
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
