#!/usr/bin/env python3
"""Tier-1 deterministic check: verify hook scoping directives.

Emits a JSON ARRAY of two envelopes per `_common.py`:

  - hook-scope (WARN): every `repo: local` hook declares
    `files:` / `types:` / `types_or:` / `exclude_types:`.
  - pass-filenames-false (WARN): every `pass_filenames: false`
    occurrence has an adjacent `# justified:` comment on the same
    or prior line.

Exit codes:
  0   — all envelopes pass / warn / inapplicable
  1   — any envelope overall_status=fail
  64  — usage error
  69  — missing required dependency (PyYAML)
  130 — interrupted

Example:
    ./check_hook_scope.py .pre-commit-config.yaml
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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_MISSING_DEP = 69
EXIT_INTERRUPTED = 130

SCOPE_KEYS = frozenset({"files", "types", "types_or", "exclude_types"})
PASS_FILENAMES_FALSE = re.compile(r"^\s*pass_filenames:\s*false\s*(#.*)?$")
JUSTIFIED = re.compile(r"#\s*justified\b", re.IGNORECASE)

_RULE_ORDER: list[str] = ["hook-scope", "pass-filenames-false"]

_RECIPE_HOOK_SCOPE = (
    "Add a scoping directive matching the file types the hook is "
    "meant to process.\n\n"
    "Example:\n"
    "    - id: validate-schema\n"
    "      entry: scripts/hooks/validate_schema.py\n"
    "        + files: ^schemas/.*\\.json$\n\n"
    "Without a scope, the hook runs on every staged file and its "
    "logic has to filter — hidden cost, harder to audit.\n"
)

_RECIPE_PASS_FILENAMES_FALSE = (
    "Either remove `pass_filenames: false` (let the framework pass "
    "the staged list) or add a `# justified: <reason>` comment on "
    "the same or prior line naming the repo-wide invariant that "
    "requires it.\n\n"
    "Example:\n"
    "    pass_filenames: false\n"
    "      -> pass_filenames: false   # justified: inspects cross-file consistency\n"
)

_RECIPES: dict[str, str] = {
    "hook-scope": _RECIPE_HOOK_SCOPE,
    "pass-filenames-false": _RECIPE_PASS_FILENAMES_FALSE,
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
        status=severity,
        location={"line": line, "context": location_context},
        reasoning=reasoning,
        recommended_changes=_RECIPES[rule_id],
    )


def _check_local_hook_scope(
    path: Path, data: dict, per_rule: dict[str, list[dict]]
) -> None:
    repos = data.get("repos")
    if not isinstance(repos, list):
        return
    for ri, repo in enumerate(repos):
        if not isinstance(repo, dict) or repo.get("repo") != "local":
            continue
        hooks = repo.get("hooks")
        if not isinstance(hooks, list):
            continue
        for hi, hook in enumerate(hooks):
            if not isinstance(hook, dict):
                continue
            if not SCOPE_KEYS.intersection(hook.keys()):
                hook_id = hook.get("id", f"<unnamed#{hi}>")
                per_rule["hook-scope"].append(
                    _make_finding(
                        "hook-scope",
                        "warn",
                        f"{path}: repos[{ri}] local hook {hook_id!r}",
                        f"`repo: local` hook {hook_id!r} in {path} "
                        "declares no `files:` / `types:` / `types_or:`.",
                    )
                )


def _check_pass_filenames_justification(
    path: Path, raw: str, per_rule: dict[str, list[dict]]
) -> None:
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if not PASS_FILENAMES_FALSE.match(line):
            continue
        same_line_comment = (
            "#" in line and JUSTIFIED.search(line.split("#", 1)[1]) is not None
        )
        prior_line = lines[i - 1] if i > 0 else ""
        prior_line_comment = JUSTIFIED.search(prior_line) is not None
        if not (same_line_comment or prior_line_comment):
            per_rule["pass-filenames-false"].append(
                _make_finding(
                    "pass-filenames-false",
                    "warn",
                    f"{path}: line {i + 1}: pass_filenames: false without `# justified:`",  # noqa: E501
                    f"Line {i + 1} of {path}: `pass_filenames: false` "
                    "without an adjacent `# justified:` comment.",
                    line=i + 1,
                )
            )


def _check_config(
    path: Path, yaml_mod, per_rule: dict[str, list[dict]]
) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml_mod.safe_load(raw)
    except (OSError, yaml_mod.YAMLError):
        return  # check_yaml_shape.py owns these FAILs
    if isinstance(data, dict):
        _check_local_hook_scope(path, data, per_rule)
    _check_pass_filenames_justification(path, raw, per_rule)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_hook_scope.py",
        description="Audit pre-commit hook scoping directives (Tier-1 deterministic check).",  # noqa: E501
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
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        for p in args.paths:
            _check_config(p, yaml, per_rule)
        envelopes = [
            emit_rule_envelope(rule_id=r, findings=per_rule[r])
            for r in _RULE_ORDER
        ]
        print_envelope(envelopes)
        any_fail = any(e["overall_status"] == "fail" for e in envelopes)
        return 1 if any_fail else 0
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
