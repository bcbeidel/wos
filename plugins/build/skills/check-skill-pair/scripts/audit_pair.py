#!/usr/bin/env python3
"""Audit a skill-pair for cross-artifact integrity (unified-pattern shape).

Emits a JSON array of envelopes per `scripts/_common.py` — one per rule_id,
regardless of which fired. Empty findings → `overall_status: pass`. 10
scripted rules across Tier-1 / Tier-2 / Tier-3.

Per-half structural compliance with the unified pattern is delegated to
`plugins/build/_shared/scripts/check_skill_pattern.py` — run that against
each half independently. This script audits PAIR-level integrity only.

Rules:

  Tier-1 (existence):
    principles-doc-presence (fail)
    build-skill-presence (fail)
    check-skill-presence (fail)
    check-rule-files-presence (fail) — check half has check-*.md or check_*.*
    routing-registration-presence (fail/warn) — both route lines present
    brief-presence (warn) — .briefs/<primitive>.brief.md with 5 required H2s

  Tier-2 (content):
    principles-doc-structure (warn) — required H2 sections in principles doc

  Tier-3 (cross-reference):
    shared-principles-path (fail) — halves reference the same principles doc
    check-half-references-principles-doc (warn) — check cites the doc
    build-to-check-handoff (warn) — build mentions /build:check-<primitive>

One judgment rule lives at `references/check-brief-content-quality.md` —
read inline by the primary agent during Tier-2 evaluation, not emitted
by this script.

Exit codes: 0 if no envelope is `fail`; 1 if any envelope is `fail`;
64 on argument error.

Example:
    python3 audit_pair.py bash-script
    python3 audit_pair.py bash-script --target plugin
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

# parents[0]=scripts, [1]=check-skill-pair, [2]=skills, [3]=build, [4]=plugins,
# [5]=repo root. This script reads paths beyond its plugin, so plugin-relative
# resolution would be wrong.
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[5]

# Primitive names are kebab-case identifiers. Validating at the CLI boundary
# keeps untrusted input out of path construction downstream.
_PRIMITIVE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")

TARGET_PREFIXES: dict[str, dict[str, str]] = {
    "plugin": {
        "skill_root": "plugins/build/skills",
        "shared_ref_dir": "plugins/build/_shared/references",
    },
    "project": {
        "skill_root": ".claude/skills",
        "shared_ref_dir": ".claude/skills/_shared/references",
    },
    "user": {
        "skill_root": "~/.claude/skills",
        "shared_ref_dir": "~/.claude/skills/_shared/references",
    },
}

REQUIRED_H2_PREFIXES = [
    "What a Good",
    "Anatomy",
    "Patterns That Work",
    "Safety",
]

REQUIRED_BRIEF_H2_PREFIXES = [
    "User ask",
    "So-what",
    "Scope boundaries",
    "Planned artifacts",
    "Planned handoffs",
]

_RULE_ORDER = [
    "principles-doc-presence",
    "build-skill-presence",
    "check-skill-presence",
    "check-rule-files-presence",
    "routing-registration-presence",
    "brief-presence",
    "principles-doc-structure",
    "shared-principles-path",
    "check-half-references-principles-doc",
    "build-to-check-handoff",
]

# ---- Recipe constants (sourced from skill-pair-best-practices.md) ----------

_RECIPE_REBUILD_PAIR = (
    "Run `/build:build-skill-pair <primitive>` to re-scaffold the missing "
    "artifact. The meta-skill's Distill / Save steps regenerate the file from "
    "the pair's input material; do not hand-author piecewise — partial "
    "scaffolds are how pair drift starts.\n\n"
    "If the principles doc is intact but a SKILL or rule file is missing, the "
    "Distill step passes through and only the missing artifact is written."
)

_RECIPE_CHECK_RULE_FILES = (
    "The check half must have at least one rule to enforce, or it audits "
    "nothing. Add either:\n\n"
    "  - A judgment rule at `check-<primitive>/references/check-<rule>.md` "
    "(unified Claude-rule shape: imperative + Why + How to apply + Example + "
    "Exception), OR\n"
    "  - A detection script at `check-<primitive>/scripts/check_<rule>.{py,sh}` "
    "emitting JSON envelopes via `_common.py` with embedded "
    "`recommended_changes` recipes.\n\n"
    "Most check halves want a mix. See `check-skill-pattern.md` "
    "§\"The Single-Artifact-Per-Rule Principle\"."
)

_RECIPE_ROUTING = (
    "Append the missing route line(s) to the appropriate section of "
    "`plugins/build/_shared/references/primitive-routing.md`:\n\n"
    "  - If the primitive is a new top-level class, add a one-paragraph entry "
    "under *What Each Primitive Was Designed For*.\n"
    "  - If it is a variant of an existing class (e.g., new language under "
    "Language Selection), extend the relevant sub-section.\n\n"
    "Both `/build:build-<primitive>` and `/build:check-<primitive>` lines must "
    "appear as literal strings somewhere in the doc."
)

_RECIPE_BRIEF = (
    "Write `.briefs/<primitive>.brief.md` per "
    "`plugins/build/_shared/references/brief-best-practices.md`. The brief is "
    "throw-away intent capture — five required H2 sections (*User ask*, "
    "*So-what*, *Scope boundaries*, *Planned artifacts*, *Planned handoffs*).\n\n"
    "A retroactive brief authored after the fact is acceptable; it does not need "
    "to reconstruct the original intake conversation, only capture what the "
    "build *should have* recorded. A missing brief is `warn` — the pair still "
    "functions, but the build that produced it lacked the intent-capture step."
)

_RECIPE_PRINCIPLES_STRUCTURE = (
    "Add the missing required H2 section(s) to the principles doc. The four "
    "required sections are:\n\n"
    "  - `## What a Good <primitive> Does`\n"
    "  - `## Anatomy`\n"
    "  - `## Patterns That Work`\n"
    "  - `## Safety` (or the longer `## Safety & Maintenance`; both pass via "
    "prefix match)\n\n"
    "If three or more are missing, route to `/build:build-skill-pair "
    "<primitive>` for a full Distill rebuild — partial principles docs produce "
    "partial rubrics."
)

_RECIPE_SHARED_PRINCIPLES = (
    "Both halves' frontmatter `references:` must resolve to the same "
    "principles-doc path. Identify the authoritative path (the one that exists "
    "on disk, or the one the principles doc itself was named with), then "
    "update the other half's `references:` block to match. Show the diff and "
    "write on confirmation. If neither path resolves, escalate to a "
    "`principles-doc-presence` rebuild."
)

_RECIPE_CHECK_FRONTMATTER = (
    "Add a relative reference to the principles doc to the check half's "
    "`references:` block: `../../_shared/references/<primitive>-best-"
    "practices.md`. The check half cites the principles doc up front so "
    "Claude loads the canonical 'Why' before reading individual rules."
)

_RECIPE_BUILD_HANDOFF = (
    "Add `/build:check-<primitive>` to the build half's Handoff section's "
    "`Chainable-to:` line, and — if the build half has a `Test` workflow step "
    "— cite the check command there as the canonical follow-on. The pair is "
    "chainable by design; the build half names its check half explicitly so "
    "users discover the audit without grepping."
)

_RECIPES: dict[str, str] = {
    "principles-doc-presence": _RECIPE_REBUILD_PAIR,
    "build-skill-presence": _RECIPE_REBUILD_PAIR,
    "check-skill-presence": _RECIPE_REBUILD_PAIR,
    "check-rule-files-presence": _RECIPE_CHECK_RULE_FILES,
    "routing-registration-presence": _RECIPE_ROUTING,
    "brief-presence": _RECIPE_BRIEF,
    "principles-doc-structure": _RECIPE_PRINCIPLES_STRUCTURE,
    "shared-principles-path": _RECIPE_SHARED_PRINCIPLES,
    "check-half-references-principles-doc": _RECIPE_CHECK_FRONTMATTER,
    "build-to-check-handoff": _RECIPE_BUILD_HANDOFF,
}


# ---- Helpers ----------------------------------------------------------------


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def extract_h2(text: str) -> list[str]:
    return [m.strip() for m in re.findall(r"^##\s+(.+)$", text, flags=re.M)]


def extract_frontmatter(text: str) -> str | None:
    match = re.match(r"^---\n(.*?)\n---", text, flags=re.S)
    return match.group(1) if match else None


def parse_references_field(frontmatter_text: str) -> list[str]:
    """Extract list items under `references:` in YAML frontmatter."""
    refs: list[str] = []
    in_refs = False
    for line in frontmatter_text.splitlines():
        stripped = line.strip()
        if not in_refs:
            if stripped == "references:":
                in_refs = True
            continue
        if line.startswith((" ", "\t")) and stripped.startswith("- "):
            refs.append(stripped[2:].strip())
        elif stripped == "":
            continue
        else:
            break
    return refs


def resolve_reference(skill_dir: Path, ref: str) -> Path:
    return (skill_dir / ref).resolve()


def resolve_target_paths(target: str, root: Path) -> tuple[Path, Path]:
    prefixes = TARGET_PREFIXES[target]
    if target == "user":
        skill_root = Path(prefixes["skill_root"]).expanduser()
        shared_ref_dir = Path(prefixes["shared_ref_dir"]).expanduser()
    else:
        skill_root = root / prefixes["skill_root"]
        shared_ref_dir = root / prefixes["shared_ref_dir"]
    return skill_root, shared_ref_dir


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def _make_finding(
    rule_id: str,
    severity: str,
    artifact: str,
    issue: str,
    line: int = 0,
) -> dict:
    """Wrap _common.emit_json_finding with the skill-pair domain shape."""
    return emit_json_finding(
        rule_id=rule_id,
        status=severity,
        location={"line": line, "context": artifact},
        reasoning=issue,
        recommended_changes=_RECIPES[rule_id],
    )


# ---- Detection ---------------------------------------------------------------


def _resolve_paths(primitive: str, root: Path, target: str) -> dict[str, Path]:
    """Return the resolved artifact paths the audit reads (existing or not)."""
    skill_root, shared_ref_dir = resolve_target_paths(target, root)
    return {
        "principles_doc": shared_ref_dir / f"{primitive}-best-practices.md",
        "build_skill": skill_root / f"build-{primitive}" / "SKILL.md",
        "check_skill": skill_root / f"check-{primitive}" / "SKILL.md",
        "routing_doc": shared_ref_dir / "primitive-routing.md",
        "check_skill_dir": skill_root / f"check-{primitive}",
    }


def detect_tier1_existence(
    primitive: str, paths: dict[str, Path], root: Path, target: str
) -> dict[str, list[dict]]:
    """Tier-1 existence findings, keyed by rule_id."""
    findings: dict[str, list[dict]] = {
        "principles-doc-presence": [],
        "build-skill-presence": [],
        "check-skill-presence": [],
        "check-rule-files-presence": [],
        "routing-registration-presence": [],
    }
    if not (
        paths["principles_doc"].is_file()
        and paths["principles_doc"].stat().st_size > 0
    ):
        findings["principles-doc-presence"].append(
            _make_finding(
                "principles-doc-presence",
                "fail",
                _rel(paths["principles_doc"], root),
                f"principles doc for primitive `{primitive}` is missing or empty",
            )
        )
    if not paths["build_skill"].is_file():
        findings["build-skill-presence"].append(
            _make_finding(
                "build-skill-presence",
                "fail",
                _rel(paths["build_skill"], root),
                "build half SKILL.md is missing",
            )
        )
    if not paths["check_skill"].is_file():
        findings["check-skill-presence"].append(
            _make_finding(
                "check-skill-presence",
                "fail",
                _rel(paths["check_skill"], root),
                "check half SKILL.md is missing",
            )
        )

    # check-rule-files-presence: the check half must have at least one rule.
    check_dir = paths["check_skill_dir"]
    if check_dir.is_dir():
        judgment_files = list((check_dir / "references").glob("check-*.md"))
        scripted_files = list((check_dir / "scripts").glob("check_*.py")) + list(
            (check_dir / "scripts").glob("check_*.sh")
        )
        if not judgment_files and not scripted_files:
            findings["check-rule-files-presence"].append(
                _make_finding(
                    "check-rule-files-presence",
                    "fail",
                    _rel(check_dir, root),
                    (
                        "check half has neither references/check-*.md (judgment "
                        "rules) nor scripts/check_*.{py,sh} (detection scripts) "
                        "— it audits nothing"
                    ),
                )
            )

    # Routing-doc registration. Required for plugin target; optional for project / user.
    routing_text = read_text(paths["routing_doc"])
    if routing_text is None:
        if target == "plugin":
            findings["routing-registration-presence"].append(
                _make_finding(
                    "routing-registration-presence",
                    "fail",
                    _rel(paths["routing_doc"], root),
                    "primitive-routing.md is missing",
                )
            )
    else:
        build_route = f"/build:build-{primitive}"
        check_route = f"/build:check-{primitive}"
        has_build = build_route in routing_text
        has_check = check_route in routing_text
        if not has_build and not has_check:
            severity = "fail" if target == "plugin" else "warn"
            findings["routing-registration-presence"].append(
                _make_finding(
                    "routing-registration-presence",
                    severity,
                    _rel(paths["routing_doc"], root),
                    f"both {build_route} and {check_route} route lines missing",
                )
            )
        elif not has_build:
            findings["routing-registration-presence"].append(
                _make_finding(
                    "routing-registration-presence",
                    "warn",
                    _rel(paths["routing_doc"], root),
                    f"{build_route} route line missing",
                )
            )
        elif not has_check:
            findings["routing-registration-presence"].append(
                _make_finding(
                    "routing-registration-presence",
                    "warn",
                    _rel(paths["routing_doc"], root),
                    f"{check_route} route line missing",
                )
            )
    return findings


def detect_brief_presence(primitive: str, root: Path) -> list[dict]:
    """Tier-1 brief-presence — file exists with 5 required H2 sections.

    Content quality (so-what specificity, scope-boundary concreteness) is the
    judgment rule check-brief-content-quality.md, evaluated by the primary
    agent during Tier-2.
    """
    brief_path = root / ".briefs" / f"{primitive}.brief.md"
    rel = _rel(brief_path, root)
    text = read_text(brief_path)
    if text is None:
        return [
            _make_finding(
                "brief-presence",
                "warn",
                rel,
                "missing — multi-artifact builds should capture intent in a brief",
            )
        ]
    findings = []
    h2s = extract_h2(text)
    for required in REQUIRED_BRIEF_H2_PREFIXES:
        if not any(h.startswith(required) for h in h2s):
            findings.append(
                _make_finding(
                    "brief-presence",
                    "warn",
                    rel,
                    f"missing required section: {required}",
                )
            )
    return findings


def detect_tier2_content(paths: dict[str, Path], root: Path) -> list[dict]:
    findings: list[dict] = []
    principles_text = read_text(paths["principles_doc"])
    if not principles_text:
        return findings
    h2s = extract_h2(principles_text)
    for required in REQUIRED_H2_PREFIXES:
        if not any(h.startswith(required) for h in h2s):
            findings.append(
                _make_finding(
                    "principles-doc-structure",
                    "warn",
                    _rel(paths["principles_doc"], root),
                    f"missing required H2 section: {required}",
                )
            )
    return findings


def detect_tier3_cross_reference(
    primitive: str, paths: dict[str, Path], root: Path
) -> dict[str, list[dict]]:
    findings: dict[str, list[dict]] = {
        "shared-principles-path": [],
        "check-half-references-principles-doc": [],
        "build-to-check-handoff": [],
    }
    build_text = read_text(paths["build_skill"])
    check_text = read_text(paths["check_skill"])

    def extract_principles_ref(skill_text: str, skill_path: Path) -> Path | None:
        fm = extract_frontmatter(skill_text or "")
        if not fm:
            return None
        for ref in parse_references_field(fm):
            if ref.endswith(f"{primitive}-best-practices.md"):
                return resolve_reference(skill_path.parent, ref)
        return None

    build_principles = (
        extract_principles_ref(build_text or "", paths["build_skill"])
        if build_text
        else None
    )
    check_principles = (
        extract_principles_ref(check_text or "", paths["check_skill"])
        if check_text
        else None
    )

    # shared-principles-path: both halves cite the principles doc, and they
    # cite the same path.
    if build_text and build_principles is None:
        findings["shared-principles-path"].append(
            _make_finding(
                "shared-principles-path",
                "fail",
                _rel(paths["build_skill"], root),
                "frontmatter references[]: does not cite the principles doc",
            )
        )
    if check_text and check_principles is None:
        findings["shared-principles-path"].append(
            _make_finding(
                "shared-principles-path",
                "fail",
                _rel(paths["check_skill"], root),
                "frontmatter references[]: does not cite the principles doc",
            )
        )
    if build_principles and check_principles and build_principles != check_principles:
        findings["shared-principles-path"].append(
            _make_finding(
                "shared-principles-path",
                "fail",
                "build/check SKILL.md references[]",
                (
                    f"halves reference different principles docs "
                    f"({_rel(build_principles, root)} vs "
                    f"{_rel(check_principles, root)})"
                ),
            )
        )

    # check-half-references-principles-doc: principles doc IS in check's references.
    # (We allow either an exact match or any path ending with the principles
    # doc filename — both are accepted by the shared-principles-path check.)
    if check_text and check_principles is None:
        findings["check-half-references-principles-doc"].append(
            _make_finding(
                "check-half-references-principles-doc",
                "warn",
                _rel(paths["check_skill"], root),
                (
                    "check half's frontmatter references[] does not cite "
                    f"`{primitive}-best-practices.md`"
                ),
            )
        )

    # build-to-check-handoff: build half mentions /build:check-<primitive>.
    if build_text:
        check_route = f"/build:check-{primitive}"
        if check_route not in build_text:
            findings["build-to-check-handoff"].append(
                _make_finding(
                    "build-to-check-handoff",
                    "warn",
                    _rel(paths["build_skill"], root),
                    f"body does not mention {check_route}",
                )
            )
    return findings


# ---- Main --------------------------------------------------------------------


def audit(primitive: str, root: Path, target: str = "plugin") -> list[dict]:
    """Return a list of envelopes (one per rule_id in _RULE_ORDER)."""
    paths = _resolve_paths(primitive, root, target)
    per_rule: dict[str, list[dict]] = {rid: [] for rid in _RULE_ORDER}

    t1 = detect_tier1_existence(primitive, paths, root, target)
    for rid, fs in t1.items():
        per_rule[rid].extend(fs)
    per_rule["brief-presence"].extend(detect_brief_presence(primitive, root))
    per_rule["principles-doc-structure"].extend(detect_tier2_content(paths, root))
    t3 = detect_tier3_cross_reference(primitive, paths, root)
    for rid, fs in t3.items():
        per_rule[rid].extend(fs)

    # If principles_doc + both SKILLs are all missing, treat the dependent
    # rule_ids as inapplicable (we can't read what doesn't exist). The
    # presence rules themselves still emit fail envelopes.
    critical_missing = sum(
        1
        for key in ("principles_doc", "build_skill", "check_skill")
        if not paths[key].is_file()
    )
    no_pair = critical_missing == 3

    envelopes: list[dict] = []
    for rid in _RULE_ORDER:
        if no_pair and rid not in (
            "principles-doc-presence",
            "build-skill-presence",
            "check-skill-presence",
        ):
            envelopes.append(
                emit_rule_envelope(rule_id=rid, findings=[], inapplicable=True)
            )
        else:
            envelopes.append(
                emit_rule_envelope(rule_id=rid, findings=per_rule[rid])
            )
    return envelopes


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a skill-pair for cross-artifact integrity.",
    )
    parser.add_argument(
        "primitive", help="Primitive name (kebab-case, no path prefix)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Repo root (default: resolved from script location).",
    )
    parser.add_argument(
        "--target",
        choices=("plugin", "project", "user"),
        default="plugin",
        help=(
            "Placement scope per skill-locations.md: plugin "
            "(plugins/build/...), project (.claude/skills/...), or user "
            "(~/.claude/skills/...). Default: plugin."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = get_parser()
    args = parser.parse_args(argv)
    if not _PRIMITIVE_NAME_RE.match(args.primitive):
        print(
            f"error: primitive name must match {_PRIMITIVE_NAME_RE.pattern} "
            f"(got: {args.primitive!r})",
            file=sys.stderr,
        )
        return 64
    try:
        envelopes = audit(args.primitive, args.root.resolve(), args.target)
    except KeyboardInterrupt:
        return 130
    print_envelope(envelopes)
    any_fail = any(e["overall_status"] == "fail" for e in envelopes)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
