#!/usr/bin/env python3
"""Structural audit: a `check-*` skill conforms to the unified pattern.

Validates a `plugins/build/skills/check-<primitive>/` directory against
`plugins/build/_shared/references/check-skill-pattern.md`. Emits a JSON
envelope per the pattern itself (single-artifact-per-rule discipline,
embedded `recommended_changes` recipes — eats its own dogfood).

Checks performed (rule_ids):

  - pattern-no-stale-artifacts:    audit-dimensions.md, repair-playbook.md,
                                   _hub.md, references/fixtures/, and
                                   references/rule-*.md must not exist
  - pattern-no-subagent-footprint: plugins/build/agents/, audit_with_dispatcher.py,
                                   invoke_subagent.py, orchestrator.py must
                                   not exist anywhere related to this skill
  - pattern-judgment-rule-shape:   each references/check-*.md has YAML
                                   frontmatter with `name:` and `description:`
  - pattern-output-example-asset:  assets/output-example.json exists and is
                                   valid JSON with `_comment`, `rule_id`,
                                   `overall_status`, `findings` keys
  - pattern-common-py-present:     scripts/_common.py + tests/test_common.py
                                   exist iff the skill has detection scripts
                                   (check_*.py or check_*.sh)
  - pattern-skill-md-references:   SKILL.md `references[]` enumerates exactly
                                   the present check-*.md files plus at least
                                   one shared best-practices doc
  - pattern-no-rule-overlap:       no rule_id appears in both
                                   references/check-*.md and a script's
                                   filename (filesystem-layer overlap check;
                                   actual emitted-rule_id overlap requires
                                   running the scripts, out of scope for the
                                   structural audit)

Exit codes: 0 if every envelope is `pass`/`inapplicable`; 1 if any
envelope is `fail`; 64 on argument error.

Example:
    python3 check_skill_pattern.py plugins/build/skills/check-bash-script
    python3 check_skill_pattern.py plugins/build/skills/check-bash-script --human
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_RECIPE_NO_STALE = (
    "Delete the legacy artifact. Convention prose belongs in "
    "`plugins/build/_shared/references/<primitive>-best-practices.md`; "
    "per-rule repair guidance belongs in each detection script's "
    "`_RECIPE_*` module constant. The filesystem (`references/check-*.md` "
    "+ scripts/check_*.{py,sh}`) is the canonical TOC — no `_hub.md` or "
    "`audit-dimensions.md` listing rules. See "
    "`plugins/build/_shared/references/check-skill-pattern.md` "
    "§\"Anatomy\" + \"Migration Workflow\" steps 4–5."
)

_RECIPE_NO_SUBAGENT = (
    "Delete any `plugins/build/agents/audit-dispatcher*` artifact, "
    "`scripts/audit_with_dispatcher.py`, `scripts/invoke_subagent.py`, "
    "or `scripts/orchestrator.py`. Tier-2 runs inline as the primary "
    "agent reading `references/check-*.md` files — no SDK dispatch, "
    "no subagent. See `check-skill-pattern.md` §\"SKILL.md\" Tier-2 "
    "subsection."
)

_RECIPE_JUDGMENT_SHAPE = (
    "Each `references/check-<rule_id>.md` must follow the unified Claude-"
    "rule shape from `rule-best-practices.md`: YAML frontmatter with "
    "`name:` and `description:` (and optional `paths:` glob), followed by "
    "imperative + Why + How to apply + optional Example + optional "
    "Exception. See `check-skill-pattern.md` §\"Judgment Rule File "
    "Contract\"."
)

_RECIPE_OUTPUT_EXAMPLE = (
    "Add `assets/output-example.json` with the canonical envelope shape: "
    "`{_comment, rule_id, overall_status, findings}`. The `_comment` "
    "documents the schema and notes that `recommended_changes` is "
    "REQUIRED. Copy the bash-script asset and swap the example `rule_id`. "
    "See `check-skill-pattern.md` §\"`assets/output-example.json`\"."
)

_RECIPE_COMMON_PY = (
    "Copy `scripts/_common.py` + `scripts/tests/{__init__.py,"
    "test_common.py}` verbatim from `check-bash-script`. Required iff the "
    "skill has any `scripts/check_*.{py,sh}` detection scripts. See "
    "`check-skill-pattern.md` §\"`_common.py`\"."
)

_RECIPE_SKILL_MD_REFS = (
    "SKILL.md `references[]` must enumerate exactly the surviving "
    "`references/check-*.md` files plus at least one shared best-"
    "practices doc (e.g., `../../_shared/references/<primitive>-best-"
    "practices.md`). Scripts are discovered by filesystem walk, not "
    "listed; `assets/output-example.json` is documentation, not eager "
    "context. See `check-skill-pattern.md` §\"SKILL.md\"."
)

_RECIPE_NO_OVERLAP = (
    "Single-artifact-per-rule violation. A rule_id must NOT appear as "
    "both `references/check-<rule>.md` and a `scripts/check_<rule>.*` "
    "script. Pick one home: script if ≥70% mechanically detectable, "
    "markdown otherwise. See `check-skill-pattern.md` §\"The Single-"
    "Artifact-Per-Rule Principle\"."
)


def emit_finding(
    rule_id: str,
    status: str,
    location: dict | None,
    reasoning: str,
    recommended_changes: str,
) -> dict:
    if status not in ("warn", "fail"):
        raise ValueError(f"status must be 'warn' or 'fail', got {status!r}")
    if not recommended_changes.strip():
        raise ValueError(f"recommended_changes required (rule_id={rule_id!r})")
    return {
        "status": status,
        "location": location,
        "reasoning": reasoning,
        "recommended_changes": recommended_changes,
    }


def envelope(rule_id: str, findings: list[dict]) -> dict:
    if any(f["status"] == "fail" for f in findings):
        overall = "fail"
    elif any(f["status"] == "warn" for f in findings):
        overall = "warn"
    else:
        overall = "pass"
    return {"rule_id": rule_id, "overall_status": overall, "findings": findings}


def check_no_stale_artifacts(skill_dir: Path) -> dict:
    findings: list[dict] = []
    refs = skill_dir / "references"
    stale_paths = [
        refs / "audit-dimensions.md",
        refs / "repair-playbook.md",
        refs / "_hub.md",
        refs / "fixtures",
    ]
    for p in stale_paths:
        if p.exists():
            findings.append(
                emit_finding(
                    rule_id="pattern-no-stale-artifacts",
                    status="fail",
                    location={"line": 0, "context": str(p.relative_to(skill_dir))},
                    reasoning=(
                        f"Legacy pre-pattern artifact `{p.relative_to(skill_dir)}` "
                        "exists; the unified pattern eliminates it."
                    ),
                    recommended_changes=_RECIPE_NO_STALE,
                )
            )
    if refs.is_dir():
        for p in sorted(refs.glob("rule-*.md")):
            findings.append(
                emit_finding(
                    rule_id="pattern-no-stale-artifacts",
                    status="fail",
                    location={"line": 0, "context": str(p.relative_to(skill_dir))},
                    reasoning=(
                        f"Legacy `rule-*.md` filename: `{p.relative_to(skill_dir)}`. "
                        "Judgment rules use the `check-*.md` prefix."
                    ),
                    recommended_changes=(
                        "Rename via `git mv references/rule-<id>.md "
                        "references/check-<id>.md` (judgment rule) OR delete the "
                        "file if its detection moved to a script (scripted rule). "
                        + _RECIPE_NO_STALE
                    ),
                )
            )
    return envelope("pattern-no-stale-artifacts", findings)


def check_no_subagent_footprint(skill_dir: Path) -> dict:
    findings: list[dict] = []
    repo_root = skill_dir.resolve().parents[3]
    suspect_paths = [
        repo_root / "plugins" / "build" / "agents" / "audit-dispatcher.md",
        repo_root / "plugins" / "build" / "agents" / "audit-dispatcher",
        skill_dir / "scripts" / "audit_with_dispatcher.py",
        skill_dir / "scripts" / "invoke_subagent.py",
        skill_dir / "scripts" / "orchestrator.py",
    ]
    for p in suspect_paths:
        if p.exists():
            findings.append(
                emit_finding(
                    rule_id="pattern-no-subagent-footprint",
                    status="fail",
                    location={"line": 0, "context": str(p)},
                    reasoning=(
                        f"Subagent dispatch artifact `{p.name}` exists. "
                        "Tier-2 runs inline; SDK dispatch was deleted."
                    ),
                    recommended_changes=_RECIPE_NO_SUBAGENT,
                )
            )
    return envelope("pattern-no-subagent-footprint", findings)


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def check_judgment_rule_shape(skill_dir: Path) -> dict:
    findings: list[dict] = []
    refs = skill_dir / "references"
    if not refs.is_dir():
        return envelope("pattern-judgment-rule-shape", findings)
    for p in sorted(refs.glob("check-*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as err:
            findings.append(
                emit_finding(
                    rule_id="pattern-judgment-rule-shape",
                    status="fail",
                    location={"line": 0, "context": str(p.relative_to(skill_dir))},
                    reasoning=f"cannot read: {err}",
                    recommended_changes=_RECIPE_JUDGMENT_SHAPE,
                )
            )
            continue
        m = _FRONTMATTER_RE.search(text)
        if not m:
            findings.append(
                emit_finding(
                    rule_id="pattern-judgment-rule-shape",
                    status="fail",
                    location={"line": 1, "context": str(p.relative_to(skill_dir))},
                    reasoning="missing YAML frontmatter delimiters (--- ... ---)",
                    recommended_changes=_RECIPE_JUDGMENT_SHAPE,
                )
            )
            continue
        fm = m.group(1)
        for required in ("name:", "description:"):
            if required not in fm:
                findings.append(
                    emit_finding(
                        rule_id="pattern-judgment-rule-shape",
                        status="fail",
                        location={
                            "line": 1,
                            "context": str(p.relative_to(skill_dir)),
                        },
                        reasoning=f"frontmatter missing `{required}` field",
                        recommended_changes=_RECIPE_JUDGMENT_SHAPE,
                    )
                )
    return envelope("pattern-judgment-rule-shape", findings)


def check_output_example_asset(skill_dir: Path) -> dict:
    findings: list[dict] = []
    asset = skill_dir / "assets" / "output-example.json"
    if not asset.exists():
        # Asset is required only if scripts exist (detection scripts produce
        # the shape this asset documents). Pure-judgment skills can skip.
        if _has_detection_scripts(skill_dir):
            findings.append(
                emit_finding(
                    rule_id="pattern-output-example-asset",
                    status="fail",
                    location=None,
                    reasoning=(
                        "scripts/check_*.{py,sh} exist but "
                        "assets/output-example.json is missing"
                    ),
                    recommended_changes=_RECIPE_OUTPUT_EXAMPLE,
                )
            )
        return envelope("pattern-output-example-asset", findings)
    try:
        data = json.loads(asset.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        findings.append(
            emit_finding(
                rule_id="pattern-output-example-asset",
                status="fail",
                location={"line": 0, "context": "assets/output-example.json"},
                reasoning=f"invalid JSON: {err}",
                recommended_changes=_RECIPE_OUTPUT_EXAMPLE,
            )
        )
        return envelope("pattern-output-example-asset", findings)
    required_keys = ("_comment", "rule_id", "overall_status", "findings")
    missing = [k for k in required_keys if k not in data]
    if missing:
        findings.append(
            emit_finding(
                rule_id="pattern-output-example-asset",
                status="fail",
                location={"line": 0, "context": "assets/output-example.json"},
                reasoning=f"missing required keys: {missing}",
                recommended_changes=_RECIPE_OUTPUT_EXAMPLE,
            )
        )
    return envelope("pattern-output-example-asset", findings)


def _has_detection_scripts(skill_dir: Path) -> bool:
    scripts = skill_dir / "scripts"
    if not scripts.is_dir():
        return False
    return bool(
        list(scripts.glob("check_*.py")) + list(scripts.glob("check_*.sh"))
    )


def check_common_py_present(skill_dir: Path) -> dict:
    findings: list[dict] = []
    if not _has_detection_scripts(skill_dir):
        return envelope("pattern-common-py-present", findings)
    common = skill_dir / "scripts" / "_common.py"
    test_common = skill_dir / "scripts" / "tests" / "test_common.py"
    if not common.exists():
        findings.append(
            emit_finding(
                rule_id="pattern-common-py-present",
                status="fail",
                location=None,
                reasoning="scripts/_common.py missing (detection scripts present)",
                recommended_changes=_RECIPE_COMMON_PY,
            )
        )
    if not test_common.exists():
        findings.append(
            emit_finding(
                rule_id="pattern-common-py-present",
                status="warn",
                location=None,
                reasoning="scripts/tests/test_common.py missing",
                recommended_changes=_RECIPE_COMMON_PY,
            )
        )
    return envelope("pattern-common-py-present", findings)


_REFERENCES_RE = re.compile(r"^references:\n((?:\s*-\s.*\n)+)", re.MULTILINE)


def check_skill_md_references(skill_dir: Path) -> dict:
    findings: list[dict] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        findings.append(
            emit_finding(
                rule_id="pattern-skill-md-references",
                status="fail",
                location=None,
                reasoning="SKILL.md missing",
                recommended_changes=_RECIPE_SKILL_MD_REFS,
            )
        )
        return envelope("pattern-skill-md-references", findings)
    text = skill_md.read_text(encoding="utf-8")
    m = _REFERENCES_RE.search(text)
    if not m:
        findings.append(
            emit_finding(
                rule_id="pattern-skill-md-references",
                status="fail",
                location={"line": 0, "context": "SKILL.md frontmatter"},
                reasoning="SKILL.md frontmatter has no `references:` block",
                recommended_changes=_RECIPE_SKILL_MD_REFS,
            )
        )
        return envelope("pattern-skill-md-references", findings)
    listed = re.findall(r"-\s+(\S+)", m.group(1))
    listed_check_md = sorted(
        Path(p).name for p in listed if Path(p).name.startswith("check-")
    )
    on_disk = sorted(p.name for p in (skill_dir / "references").glob("check-*.md"))
    if listed_check_md != on_disk:
        findings.append(
            emit_finding(
                rule_id="pattern-skill-md-references",
                status="fail",
                location={"line": 0, "context": "SKILL.md references[]"},
                reasoning=(
                    f"references[] check-*.md entries {listed_check_md} do not "
                    f"match files on disk {on_disk}"
                ),
                recommended_changes=_RECIPE_SKILL_MD_REFS,
            )
        )
    has_best_practices = any(
        "best-practices" in p or "_shared/references" in p for p in listed
    )
    if not has_best_practices:
        findings.append(
            emit_finding(
                rule_id="pattern-skill-md-references",
                status="warn",
                location={"line": 0, "context": "SKILL.md references[]"},
                reasoning=(
                    "no shared best-practices doc listed; the canonical 'Why' "
                    "doc should be in references[]"
                ),
                recommended_changes=_RECIPE_SKILL_MD_REFS,
            )
        )
    return envelope("pattern-skill-md-references", findings)


def check_no_rule_overlap(skill_dir: Path) -> dict:
    findings: list[dict] = []
    refs = skill_dir / "references"
    scripts = skill_dir / "scripts"
    judgment_ids: set[str] = set()
    if refs.is_dir():
        for p in refs.glob("check-*.md"):
            judgment_ids.add(p.stem.removeprefix("check-"))
    scripted_ids: set[str] = set()
    if scripts.is_dir():
        for p in list(scripts.glob("check_*.py")) + list(scripts.glob("check_*.sh")):
            scripted_ids.add(p.stem.removeprefix("check_").replace("_", "-"))
    overlap = sorted(judgment_ids & scripted_ids)
    for rid in overlap:
        findings.append(
            emit_finding(
                rule_id="pattern-no-rule-overlap",
                status="fail",
                location={"line": 0, "context": rid},
                reasoning=(
                    f"rule_id `{rid}` appears as both "
                    f"references/check-{rid}.md and "
                    f"scripts/check_{rid.replace('-', '_')}.* (filesystem)"
                ),
                recommended_changes=_RECIPE_NO_OVERLAP,
            )
        )
    return envelope("pattern-no-rule-overlap", findings)


_AUDITS = (
    check_no_stale_artifacts,
    check_no_subagent_footprint,
    check_judgment_rule_shape,
    check_output_example_asset,
    check_common_py_present,
    check_skill_md_references,
    check_no_rule_overlap,
)


def audit(skill_dir: Path) -> list[dict]:
    return [fn(skill_dir) for fn in _AUDITS]


def render_human(envelopes: list[dict], skill_dir: Path) -> str:
    lines = [f"\nPattern audit: {skill_dir}\n"]
    fail = warn = passes = 0
    for env in envelopes:
        rid = env["rule_id"]
        status = env["overall_status"].upper()
        n = len(env["findings"])
        marker = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "INAPPLICABLE": "—"}.get(
            status, "?"
        )
        lines.append(f"  {marker} {status:<5} {rid}  ({n} findings)")
        if status == "FAIL":
            fail += 1
        elif status == "WARN":
            warn += 1
        else:
            passes += 1
        for f in env["findings"]:
            ctx = ""
            if f.get("location"):
                ctx = f.get("location").get("context", "")
                if ctx:
                    ctx = f" — {ctx}"
            lines.append(f"      [{f['status']}]{ctx}: {f['reasoning']}")
    lines.append(f"\nSummary: {passes} pass, {warn} warn, {fail} fail\n")
    return "\n".join(lines)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "skill_dir",
        type=Path,
        help=(
            "Path to a check-* skill directory "
            "(contains SKILL.md, references/, scripts/)"
        ),
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Emit a human-readable report instead of JSON envelopes",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = get_parser()
    args = parser.parse_args(argv)
    if not args.skill_dir.is_dir():
        print(f"error: skill dir not found: {args.skill_dir}", file=sys.stderr)
        return EXIT_USAGE
    if not (args.skill_dir / "SKILL.md").exists():
        print(
            f"error: not a skill dir (no SKILL.md): {args.skill_dir}",
            file=sys.stderr,
        )
        return EXIT_USAGE
    envelopes = audit(args.skill_dir)
    if args.human:
        print(render_human(envelopes, args.skill_dir))
    else:
        json.dump(envelopes, sys.stdout, indent=2)
        sys.stdout.write("\n")
    any_fail = any(e["overall_status"] == "fail" for e in envelopes)
    return 1 if any_fail else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
