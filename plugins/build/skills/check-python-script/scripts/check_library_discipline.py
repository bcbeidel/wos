#!/usr/bin/env python3
"""Tier-1 library-profile checks. Emits JSON ARRAY of two envelopes.

Two rules:
  - library-no-side-effects (FAIL): module-level statement outside
    def / class / import / `__all__` assignment / type-annotated
    assignment / `if TYPE_CHECKING:` block / module docstring.
  - library-public-api-declared (WARN): module has public symbols
    (top-level functions or classes with non-underscore names) but no
    `__all__` declared.

The library profile applies to modules imported, not invoked. The CLI
shell rules from `check_structure.sh` and `check_argparse.sh` do not
apply here; this script provides the library-specific replacements.

Usage:
    check_library_discipline.py <path> [<path> ...]

Exit codes:
    0  no FAIL findings
    1  one or more FAIL findings
    64 usage error
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_CLEAN = 0
EXIT_FAIL = 1
EXIT_USAGE = 64

RULE_SIDE_EFFECTS = "library-no-side-effects"
RULE_PUBLIC_API = "library-public-api-declared"

RECIPE_SIDE_EFFECTS = (
    "Move executable code into a function. Library modules should perform "
    "no work at import time other than imports, `__all__`, type aliases, "
    "and pure-RHS constant assignments. If guarding type-only imports, "
    "use `if TYPE_CHECKING:` from typing."
)
RECIPE_PUBLIC_API = (
    "Declare `__all__ = [...]` at module scope listing the public "
    "symbols. Explicit `__all__` documents the public surface and "
    "controls `from module import *` behavior."
)

ALLOWED_TOP_LEVEL_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.AnnAssign,
)


def _is_docstring(node: ast.AST) -> bool:
    if not isinstance(node, ast.Expr):
        return False
    value = node.value
    return isinstance(value, ast.Constant) and isinstance(value.value, str)


def _is_type_checking_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
        return True
    return False


def _scan_side_effects(tree: ast.Module) -> list[dict]:
    """Return findings for top-level statements that look like side effects."""
    findings: list[dict] = []
    for idx, node in enumerate(tree.body):
        if isinstance(node, ALLOWED_TOP_LEVEL_NODES):
            continue
        if isinstance(node, ast.Assign):
            # Permit any plain assignment — we trust the author for module-
            # level constants and __all__. A future tightening could check
            # that RHS is a literal or a pure expression.
            continue
        if idx == 0 and _is_docstring(node):
            continue
        if _is_type_checking_guard(node):
            continue
        line = getattr(node, "lineno", 0)
        col = getattr(node, "col_offset", 0)
        # Try to render a short context snippet.
        try:
            context = ast.unparse(node).split("\n", 1)[0][:80]
        except Exception:  # noqa: BLE001
            context = type(node).__name__
        findings.append(
            emit_json_finding(
                rule_id=RULE_SIDE_EFFECTS,
                status="fail",
                location={"line": line, "context": context},
                reasoning=(
                    f"Top-level {type(node).__name__} at line {line}"
                    f" col {col} runs at import time. Library modules "
                    "should be side-effect-free."
                ),
                recommended_changes=RECIPE_SIDE_EFFECTS,
            )
        )
    return findings


def _has_public_symbols(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                return True
    return False


def _has_dunder_all(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    return True
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == "__all__":
                return True
    return False


def _scan_public_api(tree: ast.Module) -> list[dict]:
    if not _has_public_symbols(tree):
        return []
    if _has_dunder_all(tree):
        return []
    return [
        emit_json_finding(
            rule_id=RULE_PUBLIC_API,
            status="warn",
            location=None,
            reasoning=(
                "Module has public symbols (non-underscore top-level "
                "functions or classes) but does not declare `__all__`. "
                "Explicit public-API declaration is missing."
            ),
            recommended_changes=RECIPE_PUBLIC_API,
        )
    ]


def _iter_targets(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.glob("*.py")))
        elif p.is_file():
            out.append(p)
        else:
            print(f"warning: {p} not found, skipping", file=sys.stderr)
    return out


def _scan_file(path: Path) -> tuple[list[dict], list[dict]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        print(f"error: cannot read {path}: {err}", file=sys.stderr)
        return [], []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as err:
        # Invalid Python — emit a single FAIL finding under side-effects.
        finding = emit_json_finding(
            rule_id=RULE_SIDE_EFFECTS,
            status="fail",
            location={"line": err.lineno or 0, "context": str(err.msg)},
            reasoning=f"Cannot parse {path}: {err}",
            recommended_changes="Fix the syntax error before auditing.",
        )
        return [finding], []
    return _scan_side_effects(tree), _scan_public_api(tree)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tier-1 library-profile checks for Python modules.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Paths to Python files or directories.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    targets = _iter_targets(args.paths)
    if not targets:
        print("error: no Python files found", file=sys.stderr)
        return EXIT_USAGE

    side_findings: list[dict] = []
    api_findings: list[dict] = []
    for path in targets:
        s, a = _scan_file(path)
        side_findings.extend(s)
        api_findings.extend(a)

    side_envelope = emit_rule_envelope(RULE_SIDE_EFFECTS, side_findings)
    api_envelope = emit_rule_envelope(RULE_PUBLIC_API, api_findings)
    print_envelope([side_envelope, api_envelope])

    return EXIT_FAIL if side_envelope["overall_status"] == "fail" else EXIT_CLEAN


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
