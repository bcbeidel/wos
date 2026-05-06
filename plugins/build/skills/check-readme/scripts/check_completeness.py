#!/usr/bin/env python3
"""Tier-1 README completeness checker.

Emits a JSON ARRAY of five envelopes per `_common.py`:

  - license-file (FAIL): a LICENSE file exists alongside the README.
  - license-link (WARN): the README has a heading matching /license/i
    and a link to the LICENSE file.
  - contributing-link (WARN): the README has a Contributing heading
    or a link to CONTRIBUTING.md.
  - todo-markers (WARN): no TODO / FIXME / XXX markers outside fenced
    code blocks.
  - readme-gitignored (WARN): the README path is not excluded by a
    `.gitignore` in the same directory or any parent up to $PWD.

Exit codes:
  0  — all envelopes pass / warn / inapplicable
  1  — any envelope overall_status=fail
  64 — usage error

Example:
    ./check_completeness.py README.md path/to/docs/
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

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

_LICENSE_FILENAMES = (
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENSE.rst",
    "COPYING",
    "COPYING.md",
    "COPYING.txt",
)

_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LICENSE_HEADING_RE = re.compile(r"^licen[sc]e", re.IGNORECASE)
_CONTRIBUTING_HEADING_RE = re.compile(r"^contributing", re.IGNORECASE)
_LICENSE_LINK_RE = re.compile(
    r"\[[^\]]+\]\((?:\./)?(LICENSE|COPYING)[^)]*\)",
    re.IGNORECASE,
)
_CONTRIBUTING_LINK_RE = re.compile(
    r"\[[^\]]+\]\((?:\./)?CONTRIBUTING\.(md|rst|txt)[^)]*\)",
    re.IGNORECASE,
)
_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX)\b")

_RULE_ORDER: list[str] = [
    "license-file",
    "license-link",
    "contributing-link",
    "todo-markers",
    "readme-gitignored",
]

_RECIPE_LICENSE_FILE = (
    "Add a `LICENSE` file at the repository root containing the full "
    "license text (use the chooser at choosealicense.com if unsure). "
    "Without a license file, the project is `all rights reserved` by "
    "default — unusable by anyone who reads the README.\n"
)

_RECIPE_LICENSE_LINK = (
    "Add a `## License` H2 section with the SPDX identifier and a link "
    "to the LICENSE file. Readers need both the human-readable name and "
    "the canonical text; the section is the pointer.\n\n"
    "Example:\n"
    "    ## License\n"
    "    MIT — see [LICENSE](LICENSE).\n"
)

_RECIPE_CONTRIBUTING_LINK = (
    "Add a one-line Contributing section linking to `CONTRIBUTING.md` "
    "(create the file separately if absent). Silence signals "
    "`not accepting contributions`; even a one-liner beats silence.\n\n"
    "Example:\n"
    "    ## Contributing\n"
    "    See [CONTRIBUTING.md](CONTRIBUTING.md).\n"
)

_RECIPE_TODO_MARKERS = (
    "Convert to a tracked issue; remove from the README. Markers signal "
    "incompleteness to every reader; issues are where work tracks.\n\n"
    "Example:\n"
    "    TODO: add Windows instructions\n"
    "      -> Open issue #N, remove the line. Optionally link from a\n"
    "         Roadmap section.\n"
)

_RECIPE_README_GITIGNORED = (
    "Remove the `README.md` entry from `.gitignore` and commit the README. "
    "A README not in version control is not a README; it is a local "
    "note.\n"
)

_RECIPES: dict[str, str] = {
    "license-file": _RECIPE_LICENSE_FILE,
    "license-link": _RECIPE_LICENSE_LINK,
    "contributing-link": _RECIPE_CONTRIBUTING_LINK,
    "todo-markers": _RECIPE_TODO_MARKERS,
    "readme-gitignored": _RECIPE_README_GITIGNORED,
}


class _UsageError(Exception):
    pass


def _is_markdown(path: Path) -> bool:
    return path.suffix.lower() in _MD_EXTENSIONS


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_markdown(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_markdown(child):
                    files.append(child)
        else:
            print(f"check_completeness.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


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


def _strip_frontmatter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return lines
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_FENCE:
            return [""] * (idx + 1) + lines[idx + 1 :]
    return lines


def _has_license_file(readme: Path) -> bool:
    for name in _LICENSE_FILENAMES:
        if (readme.parent / name).exists():
            return True
    return False


def _parse_headings(lines: list[str]) -> list[str]:
    headings: list[str] = []
    in_fence = False
    fence_marker: str | None = None
    for line in lines:
        m = _FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence = True
                fence_marker = m.group("fence")
            elif line.startswith(fence_marker or ""):
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        h = _HEADING_RE.match(line)
        if h:
            headings.append(h.group(2).strip())
    return headings


def _check_license_link(
    path: Path, lines: list[str], body: str, per_rule: dict[str, list[dict]]
) -> None:
    headings = _parse_headings(lines)
    has_heading = any(_LICENSE_HEADING_RE.match(h) for h in headings)
    has_link = bool(_LICENSE_LINK_RE.search(body))
    if not has_heading or not has_link:
        parts: list[str] = []
        if not has_heading:
            parts.append("no `## License` heading")
        if not has_link:
            parts.append("no link to LICENSE file")
        per_rule["license-link"].append(
            _make_finding(
                "license-link",
                "warn",
                f"{path}: {'; '.join(parts)}",
                f"In {path}: {'; '.join(parts)}. Readers need both a "
                "License section and a link to the LICENSE file.",
                line=0,
            )
        )


def _check_contributing_link(
    path: Path, lines: list[str], body: str, per_rule: dict[str, list[dict]]
) -> None:
    headings = _parse_headings(lines)
    has_heading = any(_CONTRIBUTING_HEADING_RE.match(h) for h in headings)
    has_link = bool(_CONTRIBUTING_LINK_RE.search(body))
    if not has_heading and not has_link:
        per_rule["contributing-link"].append(
            _make_finding(
                "contributing-link",
                "warn",
                f"{path}: no Contributing heading or CONTRIBUTING link",
                f"{path} has no Contributing heading and no link to "
                "CONTRIBUTING.md. Silence signals `not accepting "
                "contributions`.",
                line=0,
            )
        )


def _check_todo_markers(
    path: Path, lines: list[str], per_rule: dict[str, list[dict]]
) -> None:
    in_fence = False
    fence_marker: str | None = None
    for lineno, line in enumerate(lines, 1):
        m = _FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence = True
                fence_marker = m.group("fence")
            elif line.startswith(fence_marker or ""):
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        marker = _MARKER_RE.search(line)
        if marker:
            per_rule["todo-markers"].append(
                _make_finding(
                    "todo-markers",
                    "warn",
                    f"{path}: line {lineno}: {marker.group(1)} marker",
                    f"Line {lineno} of {path}: `{marker.group(1)}` in "
                    "published README. Convert to a tracked issue.",
                    line=lineno,
                )
            )
            return


def _gitignore_patterns(dir_path: Path, stop_at: Path) -> list[tuple[Path, str]]:
    patterns: list[tuple[Path, str]] = []
    current = dir_path.resolve()
    boundary = stop_at.resolve()
    while True:
        gi = current / ".gitignore"
        if gi.exists():
            try:
                for raw in gi.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    patterns.append((current, line))
            except OSError:
                pass
        if current == boundary:
            break
        if current.parent == current:
            break
        if boundary not in current.parents:
            break
        current = current.parent
    return patterns


def _check_readme_gitignored(path: Path, per_rule: dict[str, list[dict]]) -> None:
    stop = Path.cwd().resolve()
    patterns = _gitignore_patterns(path.parent, stop)
    for base, pat in patterns:
        try:
            rel = path.resolve().relative_to(base)
        except ValueError:
            continue
        candidates = {path.name, str(rel), str(rel).lstrip("/")}
        stripped = pat.lstrip("/")
        if stripped in candidates or stripped == path.name:
            per_rule["readme-gitignored"].append(
                _make_finding(
                    "readme-gitignored",
                    "warn",
                    f"{path}: matched by `{pat}` in {base / '.gitignore'}",
                    f"{path} is matched by pattern `{pat}` in "
                    f"{base / '.gitignore'}. The README must be "
                    "version-controlled.",
                    line=0,
                )
            )
            return


def _check_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(
            f"check_completeness.py: cannot read {path}: {err}",
            file=sys.stderr,
        )
        return
    lines = _strip_frontmatter(raw)
    body = "\n".join(lines)
    if not _has_license_file(path):
        per_rule["license-file"].append(
            _make_finding(
                "license-file",
                "fail",
                f"{path}: no LICENSE file alongside README",
                f"No LICENSE / LICENSE.md / LICENSE.txt / COPYING file "
                f"found next to {path}. Without a license, the project "
                "is `all rights reserved` by default.",
                line=0,
            )
        )
    _check_license_link(path, lines, body, per_rule)
    _check_contributing_link(path, lines, body, per_rule)
    _check_todo_markers(path, lines, per_rule)
    _check_readme_gitignored(path, per_rule)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_completeness.py",
        description="Tier-1 README completeness checker (5 sub-checks).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more .md files or directories (non-recursive).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        files = _collect_targets(args.paths)
        for f in files:
            _check_file(f, per_rule)
        envelopes = [
            emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in _RULE_ORDER
        ]
        print_envelope(envelopes)
        any_fail = any(e["overall_status"] == "fail" for e in envelopes)
        return 1 if any_fail else 0
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
