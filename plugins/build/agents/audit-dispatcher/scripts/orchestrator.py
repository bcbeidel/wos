#!/usr/bin/env python3
"""Audit orchestrator: enumerate rules, dispatch to scripts or subagent.

Wires the audit-dispatcher subagent into a check-* skill's audit pipeline:

1. Enumerate `references/rule-*.md` in the skill directory.
2. Classify each rule as **scripted** (rule_id appears in any
   `scripts/check_*.py` or `scripts/check_*.sh` source) or **judgment**
   (no script mentions it — typically Tier-2 dimensions or Tier-3).
3. For scripted rules: run the relevant scripts against the artifact,
   group emitted findings by rule_id, invoke the subagent in **recipe
   mode** for each rule that fired (passing the script-emitted findings
   as input).
4. For judgment rules: invoke the subagent in **judgment mode** with
   no prior findings.
5. Return a list of structured results, one per rule.

Cost shape: scripted rules with no findings consume zero LLM calls
(trust the script). Scripted rules with findings consume one call.
Judgment rules consume one call. For a 40-rule check-bash-script audit
on a clean artifact, that's ~7 LLM calls (the judgment dimensions).

Dependencies: anthropic>=0.40 via invoke_subagent. Stdlib only here.

Example:
    python3 orchestrator.py \\
        --skill-dir plugins/build/skills/check-bash-script \\
        --artifact-file /path/to/script.sh
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Import the subagent wrapper from the sibling module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import invoke_subagent  # noqa: E402

EXIT_USAGE = 64
EXIT_SCRIPT_FAILURE = 70

# Lint-format regex for script findings.
# Matches lines like: "FAIL  /path/to/file — rule-id: detail".
_FINDING_RE = re.compile(
    r"^(?P<severity>FAIL|WARN|INFO|HINT)\s+"
    r"(?P<path>\S+)\s+—\s+"
    r"(?P<rule_id>[\w-]+):\s+"
    r"(?P<detail>.*)$"
)


def _enumerate_rules(skill_dir: Path) -> list[Path]:
    """Return paths of all references/rule-*.md files, sorted."""
    refs = skill_dir / "references"
    if not refs.is_dir():
        return []
    return sorted(refs.glob("rule-*.md"))


def _derive_rule_id(rule_path: Path) -> str:
    """Drop the `rule-` prefix and `.md` suffix."""
    return rule_path.stem.removeprefix("rule-")


# Pattern for shellcheck SC codes that may appear in rule bodies.
_SC_CODE_RE = re.compile(r"\b(SC\d{4})\b")


def _build_alt_id_map(rule_paths: list[Path]) -> dict[str, str]:
    """Return {alternate_id: our_rule_id} for IDs that scripts may emit.

    Bridges the gap between human-readable rule_ids in our files
    (e.g., `unquoted-variable-expansion`) and the IDs scripts actually
    emit when they wrap external tools (e.g., `SC2086` from shellcheck).

    Scans the rule's **frontmatter only** (not the body) — the
    description field is where each rule names its primary tool code.
    Body mentions are typically cross-references to sibling rules
    (e.g., a SC2010 file body referencing SC2012 / SC2045 siblings)
    and would cause last-writer-wins collisions if scanned.

    Extensible to other ID families (e.g., shfmt diff hunks, custom
    emit IDs) by adding more patterns. Documented as a known need
    for follow-up #407 (audit-recognition of richer bindings).
    """
    mapping: dict[str, str] = {}
    for path in rule_paths:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        end = text.find("---", 3)
        if end < 0:
            continue
        frontmatter = text[3:end]
        rid = _derive_rule_id(path)
        for sc in _SC_CODE_RE.findall(frontmatter):
            mapping[sc] = rid
    return mapping


def _classify_rules(
    skill_dir: Path,
    rule_ids: list[str],
    alt_to_canonical: dict[str, str],
) -> dict[str, bool]:
    """Return rule_id → is_scripted dict.

    A rule is **scripted** if its rule_id (or any alternate_id mapping
    to it) appears as a literal in any `scripts/check_*.py` or
    `scripts/check_*.sh` source file. The alternate-id bridge lets
    rules with human-readable names match scripts that emit external
    tool codes (e.g., shellcheck's SC2086).

    Falls back to judgment-mode for any rule_id with no script match,
    which is the safe default — the subagent can return `inapplicable`
    if the rule doesn't apply.
    """
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return {rid: False for rid in rule_ids}

    sources: list[str] = []
    for pattern in ("check_*.py", "check_*.sh"):
        for script in scripts_dir.glob(pattern):
            sources.append(script.read_text(encoding="utf-8", errors="replace"))
    combined = "\n".join(sources)

    # Reverse the alt-map: rule_id → set of alternate IDs that resolve to it.
    canonical_to_alts: dict[str, set[str]] = {}
    for alt, rid in alt_to_canonical.items():
        canonical_to_alts.setdefault(rid, set()).add(alt)

    result: dict[str, bool] = {}
    for rid in rule_ids:
        if rid in combined:
            result[rid] = True
            continue
        # Check alternate IDs (e.g., SC codes) that map to this rule.
        if any(alt in combined for alt in canonical_to_alts.get(rid, set())):
            result[rid] = True
            continue
        result[rid] = False
    return result


def _run_scripts(
    skill_dir: Path,
    artifact_path: Path,
    alt_to_canonical: dict[str, str],
) -> dict[str, list[dict]]:
    """Run all scripts against the artifact, return findings keyed by rule_id.

    Translates script-emitted IDs (e.g., shellcheck's `SC2086`) to our
    canonical rule_ids (e.g., `unquoted-variable-expansion`) via
    `alt_to_canonical`. Findings whose emitted ID has no canonical
    mapping are kept under the emitted ID — they'll surface as
    "no rule file matched" in downstream consumers.
    """
    scripts_dir = skill_dir / "scripts"
    findings: dict[str, list[dict]] = {}

    if not scripts_dir.is_dir():
        return findings

    for pattern in ("check_*.py", "check_*.sh"):
        for script in sorted(scripts_dir.glob(pattern)):
            cmd = (
                ["python3", str(script)]
                if script.suffix == ".py"
                else ["bash", str(script)]
            )
            cmd.append(str(artifact_path))
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, check=False, timeout=60
                )
            except subprocess.TimeoutExpired:
                continue
            for line in proc.stdout.splitlines():
                m = _FINDING_RE.match(line)
                if not m:
                    continue
                emitted_id = m.group("rule_id")
                rid = alt_to_canonical.get(emitted_id, emitted_id)
                # Try to extract a line number from detail when present.
                detail = m.group("detail")
                line_match = re.search(r"line\s+(\d+)", detail)
                location: dict = {}
                if line_match:
                    location["line"] = int(line_match.group(1))
                location["context"] = detail
                findings.setdefault(rid, []).append(
                    {
                        "severity": m.group("severity"),
                        "location": location,
                        "detail": detail,
                    }
                )
    return findings


def audit(
    skill_dir: Path,
    artifact_path: Path,
    *,
    rules_filter: list[str] | None = None,
    invoke_fn=invoke_subagent.invoke_subagent,
) -> list[dict]:
    """Run a full audit of one artifact against all of a skill's rules.

    Args:
        skill_dir: Path to the check-* skill (contains references/ and scripts/).
        artifact_path: Path to the artifact under audit.
        rules_filter: Optional list of rule_ids to restrict to. When None,
            all rules in references/rule-*.md run.
        invoke_fn: Subagent invocation function. Override in tests.

    Returns:
        List of dicts, one per rule, matching the report_audit_finding
        tool's output shape — plus an extra `mode` field ("recipe",
        "judgment", or "skipped-no-script-findings") for diagnostics.
    """
    rule_paths = _enumerate_rules(skill_dir)
    if rules_filter:
        rule_paths = [p for p in rule_paths if _derive_rule_id(p) in set(rules_filter)]
    rule_ids = [_derive_rule_id(p) for p in rule_paths]

    alt_to_canonical = _build_alt_id_map(rule_paths)
    is_scripted = _classify_rules(skill_dir, rule_ids, alt_to_canonical)
    script_findings = _run_scripts(skill_dir, artifact_path, alt_to_canonical)
    artifact_text = artifact_path.read_text(encoding="utf-8", errors="replace")

    results: list[dict] = []
    for rule_path, rid in zip(rule_paths, rule_ids):
        rule_md = rule_path.read_text(encoding="utf-8")
        findings_for_rule = script_findings.get(rid, [])

        if is_scripted[rid]:
            if not findings_for_rule:
                # Trust the script: no findings → pass; no subagent call.
                results.append(
                    {
                        "rule_id": rid,
                        "overall_status": "pass",
                        "findings": [],
                        "mode": "skipped-no-script-findings",
                    }
                )
                continue
            # Recipe mode.
            result = invoke_fn(rule_md, artifact_text, findings=findings_for_rule)
            result["mode"] = "recipe"
            results.append(result)
        else:
            # Judgment mode.
            result = invoke_fn(rule_md, artifact_text, findings=None)
            result["mode"] = "judgment"
            results.append(result)

    return results


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--skill-dir",
        required=True,
        type=Path,
        help="Path to the check-* skill (contains references/ and scripts/)",
    )
    parser.add_argument(
        "--artifact-file",
        required=True,
        type=Path,
        help="Path to the artifact under audit",
    )
    parser.add_argument(
        "--rules",
        default=None,
        help="Optional comma-separated rule_ids to restrict the audit to",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify rules and run scripts; print plan; skip subagent calls",
    )
    return parser


def _dry_run(
    skill_dir: Path, artifact_path: Path, rules_filter: list[str] | None
) -> dict:
    """Return classification + script findings without calling the subagent."""
    rule_paths = _enumerate_rules(skill_dir)
    if rules_filter:
        rule_paths = [p for p in rule_paths if _derive_rule_id(p) in set(rules_filter)]
    rule_ids = [_derive_rule_id(p) for p in rule_paths]
    alt_to_canonical = _build_alt_id_map(rule_paths)
    is_scripted = _classify_rules(skill_dir, rule_ids, alt_to_canonical)
    findings = _run_scripts(skill_dir, artifact_path, alt_to_canonical)
    plan = []
    for rid in rule_ids:
        if is_scripted[rid]:
            mode = "recipe" if findings.get(rid) else "skipped-no-script-findings"
        else:
            mode = "judgment"
        plan.append(
            {
                "rule_id": rid,
                "scripted": is_scripted[rid],
                "script_findings": findings.get(rid, []),
                "mode": mode,
            }
        )
    return {
        "skill_dir": str(skill_dir),
        "artifact": str(artifact_path),
        "rule_count": len(rule_ids),
        "plan": plan,
    }


def main(argv: list[str] | None = None) -> int:
    parser = get_parser()
    args = parser.parse_args(argv)

    if not args.skill_dir.is_dir():
        print(f"error: skill dir not found: {args.skill_dir}", file=sys.stderr)
        return EXIT_USAGE
    if not args.artifact_file.exists():
        print(f"error: artifact file not found: {args.artifact_file}", file=sys.stderr)
        return EXIT_USAGE

    rules_filter = (
        [r.strip() for r in args.rules.split(",") if r.strip()] if args.rules else None
    )

    if args.dry_run:
        print(
            json.dumps(
                _dry_run(args.skill_dir, args.artifact_file, rules_filter), indent=2
            )
        )
        return 0

    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return EXIT_USAGE

    try:
        results = audit(args.skill_dir, args.artifact_file, rules_filter=rules_filter)
    except invoke_subagent.SubagentToolCallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_SCRIPT_FAILURE

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
