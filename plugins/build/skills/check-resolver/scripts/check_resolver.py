#!/usr/bin/env python3
"""Tier-1 RESOLVER.md managed-region checks — emits JSON ARRAY of seven envelopes.

Given a target directory, walks up to the nearest ``RESOLVER.md`` and
audits that resolver. The discovered ancestor becomes the resolver
root, and all checks scope to its subtree (not the filesystem repo).

Seven rules per resolver root:

- **markers-present** (FAIL) — both ``<!-- resolver:begin -->`` and
  ``<!-- resolver:end -->`` appear exactly once.
- **filing-paths-resolve** (FAIL) — every Location column value in the
  filing table resolves to a directory on disk.
- **context-paths-resolve** (FAIL) — every doc path in the context table's
  "Load first" column resolves to a file or directory on disk.
- **filing-rows-unique** (FAIL) — the filing table's first column
  (content-type) has no duplicates.
- **context-rows-unique** (FAIL) — the context table's first column (task)
  has no duplicates.
- **dark-capability** (WARN) — every depth 1–2 directory under the resolver
  root is classified by filing table, context table, out-of-scope list,
  the ambient default set, or a nested ``RESOLVER.md`` (delegation).
- **mtime-stale** (WARN) — RESOLVER.md mtime older than 90 days.

Paths containing template placeholders (``<...>``, ``*``) are skipped
by the resolver checks — they are documented templates, not concrete paths.

Multi-target invocation: each target is one repo root; findings accumulate
across targets, then one envelope per rule_id is emitted.

Exit codes:
  0  — overall_status pass / warn / inapplicable for every emitted envelope
  1  — overall_status=fail for any envelope
  64 — usage error

Example:
    ./check_resolver.py .
    ./check_resolver.py /path/to/repo-a /path/to/repo-b
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

RESOLVER_FILENAME = "RESOLVER.md"
MARKER_BEGIN = "<!-- resolver:begin -->"
MARKER_END = "<!-- resolver:end -->"
SECONDS_PER_DAY = 24 * 60 * 60
STALE_DAYS = 90
STALE_SECONDS = STALE_DAYS * SECONDS_PER_DAY

# Directories ignored by the dark-capability scan regardless of resolver
# contents. Mirrors the ambient list documented in audit-dimensions.md.
# `.resolver` is the resolver's own machinery (siblings to RESOLVER.md).
AMBIENT_BASENAMES = frozenset(
    {
        ".git",
        "node_modules",
        "dist",
        "build",
        ".cache",
        ".venv",
        "target",
        "__pycache__",
        ".resolver",
    }
)

H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
SEPARATOR_ROW_RE = re.compile(r"^\s*\|[\s\-|:]+\|\s*$")
PLACEHOLDER_RE = re.compile(r"[<>*]")
OOS_BULLET_LINE_RE = re.compile(r"^\s*[-*]\s+")
OOS_PATH_RE = re.compile(r"`([^`]+)`")

_RULE_ORDER: list[str] = [
    "markers-present",
    "filing-paths-resolve",
    "context-paths-resolve",
    "filing-rows-unique",
    "context-rows-unique",
    "dark-capability",
    "mtime-stale",
]

_RECIPES: dict[str, str] = {
    "markers-present": (
        "Restore `<!-- resolver:begin -->` and `<!-- resolver:end -->` "
        "around the filing/context/out-of-scope section, then regenerate "
        "via `/build:build-resolver --regenerate`. Each marker must appear "
        "exactly once. Without markers, regeneration stomps human prose "
        "and the auditor cannot distinguish disk-derived content from "
        "hand edits."
    ),
    "filing-paths-resolve": (
        "Either remove the row (if the directory was intentionally deleted) "
        "or restore the directory (if it should exist). Example: a filing "
        "row `| design | .designs/ | … |` with no `.designs/` on disk → "
        "either delete the row or `mkdir .designs/` and seed it with a "
        "file matching the row's naming pattern. A filing row that doesn't "
        "resolve routes new content into nothing."
    ),
    "context-paths-resolve": (
        "Update the path to its current location (file or directory), or "
        "remove the entry from the bundle. Example: a bundle that lists "
        "`_shared/references/hook-best-practices.md` at a path no longer "
        "present → correct to `plugins/build/_shared/references/"
        "hook-best-practices.md`. A directory entry like `.research/` is "
        "also valid — the agent uses Glob on the directory's naming "
        "pattern and reads frontmatter to find the right file. Broken "
        "context loads train Claude to skip the resolver."
    ),
    "filing-rows-unique": (
        "Merge the duplicates, keeping the more specific location. "
        "Example: two filing rows both using content-type `research`, one "
        "pointing at `.research/` and one at `.docs/research/` → one row. "
        "If both locations are real, promote to a glob pattern or rename "
        "one content-type to disambiguate. Two rows routing the same "
        "content-type produce inconsistent filing decisions."
    ),
    "context-rows-unique": (
        "Merge the duplicates, keeping the broader or more recent bundle. "
        "Example: two context rows both for task `authoring a hook`, with "
        "overlapping but non-identical doc lists → one row listing the "
        "union (capped at 1–4 entries per Dimension 2). Two rows for the "
        "same task produce inconsistent context loads."
    ),
    "dark-capability": (
        "Classify the directory explicitly — add it as a filing row, a "
        "context-load target, or an out-of-scope entry; or place a nested "
        "`RESOLVER.md` inside it to delegate. Example: `.inbox/` present "
        "with 10 files but no classification → either "
        "`| inbox note | .inbox/ | <slug>.md |` in the filing table, or "
        "`- .inbox/ — transient ingress` in out-of-scope. Regenerate via "
        "`/build:build-resolver --regenerate`. Unclassified directories "
        "are capabilities Claude can't reach; silence is ambiguous."
    ),
    "mtime-stale": (
        "Run `/build:build-resolver --regenerate` to refresh the managed "
        "region against current disk state. Long-stale resolvers drift "
        "from the directories they claim to route — new directories are "
        "unclassified, deleted ones still appear in the table."
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


def extract_managed_region(text: str) -> str | None:
    begin_count = text.count(MARKER_BEGIN)
    end_count = text.count(MARKER_END)
    if begin_count != 1 or end_count != 1:
        return None
    start = text.index(MARKER_BEGIN) + len(MARKER_BEGIN)
    end = text.index(MARKER_END)
    if end <= start:
        return None
    return text[start:end]


def parse_table_cells(row_line: str) -> list[str]:
    match = TABLE_ROW_RE.match(row_line)
    if not match:
        return []
    inner = match.group(1)
    return [cell.strip() for cell in inner.split("|")]


def find_section_table(region: str, section_prefix: str) -> list[list[str]]:
    """Return data rows from the first markdown table inside the named H2 section."""
    lines = region.splitlines()
    in_section = False
    table_started = False
    data_rows: list[list[str]] = []
    prefix_lower = section_prefix.lower()

    for line in lines:
        h2_match = H2_RE.match(line)
        if h2_match:
            heading = h2_match.group(1).strip().lower()
            if heading.startswith(prefix_lower):
                in_section = True
                table_started = False
                continue
            if in_section:
                break
            continue
        if not in_section:
            continue
        if TABLE_ROW_RE.match(line):
            if SEPARATOR_ROW_RE.match(line):
                table_started = True
                continue
            if not table_started:
                continue
            cells = parse_table_cells(line)
            if cells:
                data_rows.append(cells)
        elif table_started and not line.strip():
            break
    return data_rows


def strip_backticks(value: str) -> str:
    return value.strip().strip("`").strip()


def extract_paths_from_load_cell(cell: str) -> list[str]:
    """Parse one context-table "Load first" cell into a list of doc paths."""
    inner = cell.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    parts = [strip_backticks(p) for p in inner.split(",")]
    return [p for p in parts if p]


def check_markers(
    resolver_path: Path, text: str, per_rule: dict[str, list[dict]]
) -> bool:
    begin_count = text.count(MARKER_BEGIN)
    end_count = text.count(MARKER_END)
    if begin_count == 1 and end_count == 1:
        return True
    per_rule["markers-present"].append(
        _make_finding(
            "markers-present",
            "FAIL",
            f"{resolver_path}: expected exactly one {MARKER_BEGIN} "
            f"and one {MARKER_END}; found {begin_count} begin, {end_count} end",
            f"Managed-region markers are unbalanced ({begin_count} begin, "
            f"{end_count} end); regeneration would stomp human prose and "
            "auditing cannot distinguish disk-derived content from hand edits.",
        )
    )
    return False


def check_filing_table(
    resolver_path: Path,
    resolver_root: Path,
    region: str,
    per_rule: dict[str, list[dict]],
) -> None:
    rows = find_section_table(region, "Filing")
    seen_keys: dict[str, int] = {}
    for idx, cells in enumerate(rows, start=1):
        if len(cells) < 2:
            continue
        content_type = strip_backticks(cells[0])
        location = strip_backticks(cells[1])
        if not content_type or not location:
            continue
        if content_type in seen_keys:
            per_rule["filing-rows-unique"].append(
                _make_finding(
                    "filing-rows-unique",
                    "FAIL",
                    f"{resolver_path}: duplicate content-type '{content_type}' "
                    f"(rows {seen_keys[content_type]} and {idx})",
                    f"Two filing rows share content-type '{content_type}' "
                    f"(rows {seen_keys[content_type]} and {idx}); routing "
                    "decisions become inconsistent.",
                )
            )
        else:
            seen_keys[content_type] = idx
        if PLACEHOLDER_RE.search(location):
            continue
        resolved = (resolver_root / location).resolve()
        if not resolved.is_dir():
            per_rule["filing-paths-resolve"].append(
                _make_finding(
                    "filing-paths-resolve",
                    "FAIL",
                    f"{resolver_path}: filing location '{location}' "
                    f"(content-type '{content_type}') does not resolve "
                    "to a directory",
                    f"Filing row '{content_type}' points at '{location}' "
                    "but no such directory exists; new content of this type "
                    "would be routed into nothing.",
                )
            )


def check_context_table(
    resolver_path: Path,
    resolver_root: Path,
    region: str,
    per_rule: dict[str, list[dict]],
) -> None:
    rows = find_section_table(region, "Context")
    seen_tasks: dict[str, int] = {}
    for idx, cells in enumerate(rows, start=1):
        if len(cells) < 2:
            continue
        task = strip_backticks(cells[0])
        load_cell = cells[1]
        if not task or not load_cell.strip():
            continue
        if task in seen_tasks:
            per_rule["context-rows-unique"].append(
                _make_finding(
                    "context-rows-unique",
                    "FAIL",
                    f"{resolver_path}: duplicate task '{task}' "
                    f"(rows {seen_tasks[task]} and {idx})",
                    f"Two context rows share task '{task}' (rows "
                    f"{seen_tasks[task]} and {idx}); context loads become "
                    "inconsistent depending on which row Claude reads.",
                )
            )
        else:
            seen_tasks[task] = idx
        for doc_path in extract_paths_from_load_cell(load_cell):
            if PLACEHOLDER_RE.search(doc_path):
                continue
            resolved = (resolver_root / doc_path).resolve()
            if not resolved.exists():
                per_rule["context-paths-resolve"].append(
                    _make_finding(
                        "context-paths-resolve",
                        "FAIL",
                        f"{resolver_path}: context doc '{doc_path}' "
                        f"(task '{task}') does not resolve to a file or directory",
                        f"Context row for task '{task}' lists '{doc_path}' "
                        "but the path does not exist; broken context loads "
                        "train Claude to skip the resolver.",
                    )
                )


def parse_out_of_scope(region: str) -> set[str]:
    """Extract directory paths from the 'Out of scope' bullet list."""
    paths: set[str] = set()
    in_section = False
    for line in region.splitlines():
        h2 = H2_RE.match(line)
        if h2:
            heading = h2.group(1).strip().lower()
            if heading.startswith("out of scope"):
                in_section = True
                continue
            if in_section:
                break
            continue
        if not in_section:
            continue
        if not OOS_BULLET_LINE_RE.match(line):
            continue
        for match in OOS_PATH_RE.finditer(line):
            paths.add(match.group(1).strip().rstrip("/"))
    return paths


def collect_classified(region: str) -> tuple[set[str], set[str], set[str]]:
    """Return (filing_dirs, recursive_dirs, oos_dirs) drawn from the managed region."""
    filing_dirs: set[str] = set()
    for cells in find_section_table(region, "Filing"):
        if len(cells) < 2:
            continue
        location = strip_backticks(cells[1]).rstrip("/")
        if location and not PLACEHOLDER_RE.search(location):
            filing_dirs.add(location)
    context_dirs: set[str] = set()
    for cells in find_section_table(region, "Context"):
        if len(cells) < 2:
            continue
        for doc_path in extract_paths_from_load_cell(cells[1]):
            if PLACEHOLDER_RE.search(doc_path):
                continue
            context_dirs.add(doc_path.rstrip("/"))
    oos_dirs = parse_out_of_scope(region)
    recursive_dirs = context_dirs | oos_dirs
    return filing_dirs, recursive_dirs, oos_dirs


def is_classified(rel: str, filing_dirs: set[str], recursive_dirs: set[str]) -> bool:
    if rel in filing_dirs or rel in recursive_dirs:
        return True
    if any(rel.startswith(p + "/") for p in recursive_dirs):
        return True
    rel_prefix = rel + "/"
    return any(p.startswith(rel_prefix) for p in (filing_dirs | recursive_dirs))


def is_under_oos(rel: str, oos: set[str]) -> bool:
    return rel in oos or any(rel.startswith(prefix + "/") for prefix in oos)


def emit_dark(
    resolver_path: Path, rel: str, per_rule: dict[str, list[dict]]
) -> None:
    per_rule["dark-capability"].append(
        _make_finding(
            "dark-capability",
            "WARN",
            f"{resolver_path}: directory '{rel}/' not in filing table, "
            "context table, or out of scope",
            f"Directory '{rel}/' exists on disk but is unclassified — "
            "the resolver cannot route filing or context decisions through "
            "it; capability is dark.",
        )
    )


def scan_subdir(
    resolver_path: Path,
    entry: Path,
    rel: str,
    filing_dirs: set[str],
    recursive_dirs: set[str],
    per_rule: dict[str, list[dict]],
) -> None:
    """Scan one depth-1 directory's children."""
    try:
        children = sorted(entry.iterdir())
    except (OSError, PermissionError):
        return
    for sub in children:
        if not sub.is_dir():
            continue
        if sub.name in AMBIENT_BASENAMES:
            continue
        if (sub / RESOLVER_FILENAME).is_file():
            continue
        sub_rel = f"{rel}/{sub.name}"
        if is_classified(sub_rel, filing_dirs, recursive_dirs):
            continue
        emit_dark(resolver_path, sub_rel, per_rule)


def check_dark_capabilities(
    resolver_path: Path,
    resolver_root: Path,
    region: str,
    per_rule: dict[str, list[dict]],
) -> None:
    """Walk depth 1–2 directories and warn on any unclassified entry."""
    filing_dirs, recursive_dirs, oos_dirs = collect_classified(region)
    try:
        depth1 = sorted(resolver_root.iterdir())
    except (OSError, PermissionError) as err:
        print(
            f"check_resolver.py: cannot list {resolver_root}: {err}",
            file=sys.stderr,
        )
        return
    for entry in depth1:
        if not entry.is_dir():
            continue
        name = entry.name
        if name in AMBIENT_BASENAMES:
            continue
        if (entry / RESOLVER_FILENAME).is_file():
            continue
        rel = name
        if not is_classified(rel, filing_dirs, recursive_dirs):
            emit_dark(resolver_path, rel, per_rule)
            continue
        if is_under_oos(rel, oos_dirs):
            continue
        scan_subdir(
            resolver_path, entry, rel, filing_dirs, recursive_dirs, per_rule
        )


def check_mtime(resolver_path: Path, per_rule: dict[str, list[dict]]) -> None:
    age_seconds = time.time() - resolver_path.stat().st_mtime
    if age_seconds > STALE_SECONDS:
        days = int(age_seconds / SECONDS_PER_DAY)
        per_rule["mtime-stale"].append(
            _make_finding(
                "mtime-stale",
                "WARN",
                f"{resolver_path}: RESOLVER.md mtime is {days} days old "
                f"(threshold {STALE_DAYS})",
                f"RESOLVER.md has not been touched in {days} days, beyond "
                f"the {STALE_DAYS}-day staleness threshold; routing tables "
                "may have drifted from current disk state.",
            )
        )


def find_resolver_root(target: Path) -> Path | None:
    """Walk up from ``target`` returning the nearest dir with RESOLVER.md."""
    current = target.resolve()
    for _ in range(64):
        if (current / RESOLVER_FILENAME).is_file():
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def check_target(target: Path, per_rule: dict[str, list[dict]]) -> None:
    if not target.is_dir():
        print(f"check_resolver.py: not a directory: {target}", file=sys.stderr)
        raise _UsageError
    resolver_root = find_resolver_root(target)
    if resolver_root is None:
        per_rule["markers-present"].append(
            _make_finding(
                "markers-present",
                "FAIL",
                f"{target / RESOLVER_FILENAME}: no {RESOLVER_FILENAME} "
                f"found walking up from {target}",
                f"No {RESOLVER_FILENAME} exists at or above the target; "
                "there is no resolver to audit.",
            )
        )
        return
    resolver_path = resolver_root / RESOLVER_FILENAME
    try:
        text = resolver_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(
            f"check_resolver.py: cannot read {resolver_path}: {err}",
            file=sys.stderr,
        )
        return
    markers_ok = check_markers(resolver_path, text, per_rule)
    # mtime check runs regardless of marker outcome (preserves prior behaviour)
    if not markers_ok:
        check_mtime(resolver_path, per_rule)
        return
    region = extract_managed_region(text)
    if region is None:
        return
    check_filing_table(resolver_path, resolver_root, region, per_rule)
    check_context_table(resolver_path, resolver_root, region, per_rule)
    check_dark_capabilities(resolver_path, resolver_root, region, per_rule)
    check_mtime(resolver_path, per_rule)


class _UsageError(Exception):
    pass


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_resolver.py",
        description=(
            "Tier-1 deterministic checks for the RESOLVER.md managed "
            "region (JSON envelope output)."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="One or more target directories (defaults to current "
        "directory). Walks up to the nearest RESOLVER.md and audits "
        "that resolver.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
    try:
        for target in args.paths:
            check_target(target, per_rule)
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
