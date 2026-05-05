#!/usr/bin/env python3
"""Audit orchestrator: union-discovery dispatch over scripts + markdown rules.

Wires the audit-dispatcher subagent into a check-* skill's audit pipeline
under the unified single-artifact-per-rule discipline:

1. Discover rules from the **union** of two disjoint sources:
   - `references/check-*.md` files → judgment rules (LLM-judged dimensions).
   - `scripts/check_*.{py,sh}` outputs → scripted rules (rule_ids extracted
     from each script's emitted JSON envelope).

2. Assert disjointness — a rule_id must NOT appear in both sources.
   Overlap means a rule has two artifacts; the discipline says one.

3. Dispatch:
   - Scripted rules: include the script's emitted findings directly. No
     subagent call. The script's `recommended_changes` is canonical.
   - Judgment rules: invoke the subagent in judgment-mode (no `findings`
     argument — recipe-mode is gone). Override the model-emitted
     `rule_id` with the filename-derived one (defensive against drift).

Cost shape: scripted rules consume zero LLM calls. Judgment rules
consume one call each. For a 40-rule check-bash-script audit, that's
6 LLM calls (the 6 surviving judgment dimensions) regardless of
artifact content.

Dependencies: anthropic>=0.40 via invoke_subagent. Stdlib only here.

Example:
    python3 orchestrator.py \\
        --skill-dir plugins/build/skills/check-bash-script \\
        --artifact-file /path/to/script.sh
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Import the subagent wrapper from the sibling module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import invoke_subagent  # noqa: E402

EXIT_USAGE = 64
EXIT_SCRIPT_FAILURE = 70


def _enumerate_judgment_rules(skill_dir: Path) -> list[Path]:
    """Return paths of all `references/check-*.md` files, sorted.

    These are judgment-mode rules (LLM-judged dimensions). The
    filename `check-<rule_id>.md` carries the canonical rule_id.
    """
    refs = skill_dir / "references"
    if not refs.is_dir():
        return []
    return sorted(refs.glob("check-*.md"))


def _derive_rule_id(rule_path: Path) -> str:
    """Drop the `check-` (or legacy `rule-`) prefix and `.md` suffix."""
    stem = rule_path.stem
    if stem.startswith("check-"):
        return stem.removeprefix("check-")
    if stem.startswith("rule-"):
        return stem.removeprefix("rule-")
    return stem


def _enumerate_scripts(skill_dir: Path) -> list[Path]:
    """Return executable detection scripts, sorted."""
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []
    out: list[Path] = []
    for pattern in ("check_*.py", "check_*.sh"):
        out.extend(sorted(scripts_dir.glob(pattern)))
    # `_common.py` and `tests/` are filtered by the `check_` prefix already.
    return out


def _run_one_script(
    script: Path, artifact_path: Path
) -> list[dict]:
    """Run a script and return a list of envelope dicts.

    Each script emits either a single JSON envelope (single-rule script)
    or a JSON array of envelopes (multi-rule script). We normalize to a
    list of envelope dicts. Malformed JSON, timeout, or non-JSON output
    yields an empty list — the orchestrator treats it as a no-op.
    """
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
        return []
    out = proc.stdout.strip()
    if not out:
        return []
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [e for e in parsed if isinstance(e, dict)]
    return []


def _run_all_scripts(
    skill_dir: Path, artifact_path: Path
) -> dict[str, dict]:
    """Run every script and return rule_id → envelope dict.

    The script's `rule_id` per envelope is authoritative. Later scripts
    emitting the same rule_id overwrite earlier ones (treated as a
    misconfiguration, but doesn't crash). Each envelope is a complete
    `{rule_id, overall_status, findings}` shape.
    """
    envelopes: dict[str, dict] = {}
    for script in _enumerate_scripts(skill_dir):
        for env in _run_one_script(script, artifact_path):
            rid = env.get("rule_id")
            if not rid:
                continue
            envelopes[rid] = env
    return envelopes


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
        rules_filter: Optional list of rule_ids to restrict to.
        invoke_fn: Subagent invocation function (judgment-mode only).
            Override in tests. Signature: (rule_md, artifact) -> dict.

    Returns:
        List of dicts, one per rule, each matching the report_audit_finding
        tool's output shape — plus an extra `mode` field ("scripted" or
        "judgment") for diagnostics.
    """
    judgment_paths = _enumerate_judgment_rules(skill_dir)
    judgment_ids = {_derive_rule_id(p): p for p in judgment_paths}

    script_envelopes = _run_all_scripts(skill_dir, artifact_path)
    scripted_ids = set(script_envelopes.keys())

    overlap = scripted_ids & set(judgment_ids.keys())
    if overlap:
        raise ValueError(
            f"Single-artifact-per-rule violation: rule_ids appear in both "
            f"references/check-*.md and scripts/check_*.* outputs: "
            f"{sorted(overlap)}. Each rule must have exactly one artifact."
        )

    # Apply filter if provided.
    if rules_filter:
        keep = set(rules_filter)
        judgment_ids = {k: v for k, v in judgment_ids.items() if k in keep}
        scripted_ids = scripted_ids & keep

    artifact_text = artifact_path.read_text(encoding="utf-8", errors="replace")
    results: list[dict] = []

    # Scripted rules: pass through the script's envelope as-is.
    for rid in sorted(scripted_ids):
        env = dict(script_envelopes[rid])  # shallow copy
        env["mode"] = "scripted"
        results.append(env)

    # Judgment rules: judgment-mode subagent call.
    for rid in sorted(judgment_ids):
        rule_path = judgment_ids[rid]
        rule_md = rule_path.read_text(encoding="utf-8")
        result = invoke_fn(rule_md, artifact_text)
        # Defensive: override the model-emitted rule_id with the
        # filename-derived one (model drift seen in live smoke).
        result = dict(result)
        result["rule_id"] = rid
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
        help="Discover rules + run scripts; print plan; skip subagent calls",
    )
    return parser


def _dry_run(
    skill_dir: Path, artifact_path: Path, rules_filter: list[str] | None
) -> dict:
    """Return discovery + script results without calling the subagent."""
    judgment_paths = _enumerate_judgment_rules(skill_dir)
    judgment_ids = {_derive_rule_id(p) for p in judgment_paths}
    script_envelopes = _run_all_scripts(skill_dir, artifact_path)
    scripted_ids = set(script_envelopes.keys())

    overlap = sorted(scripted_ids & judgment_ids)

    if rules_filter:
        keep = set(rules_filter)
        judgment_ids = judgment_ids & keep
        scripted_ids = scripted_ids & keep

    plan: list[dict] = []
    for rid in sorted(scripted_ids):
        env = script_envelopes[rid]
        plan.append(
            {
                "rule_id": rid,
                "mode": "scripted",
                "overall_status": env.get("overall_status"),
                "finding_count": len(env.get("findings", [])),
            }
        )
    for rid in sorted(judgment_ids):
        plan.append({"rule_id": rid, "mode": "judgment"})

    return {
        "skill_dir": str(skill_dir),
        "artifact": str(artifact_path),
        "judgment_rule_count": len(judgment_ids),
        "scripted_rule_count": len(scripted_ids),
        "rule_count": len(judgment_ids) + len(scripted_ids),
        "overlap": overlap,
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
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
