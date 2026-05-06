#!/usr/bin/env python3
"""check_cisco.py — Tier-1 wrapper around cisco-ai-skill-scanner.

Emits a JSON ARRAY of two envelopes (rule_id="scanner-fail",
rule_id="scanner-warn") per `_common.py`.

Maps each input path to its parent skill directory and runs the
scanner once per dir. Static analyzers only by default. Pass --llm
(or set SCAN_USE_LLM=1) to add the LLM analyzer; that path requires
ANTHROPIC_API_KEY in the environment.

Severity mapping:
  CRITICAL / HIGH -> rule_id="scanner-fail" (status=fail)
  MEDIUM          -> rule_id="scanner-warn" (status=warn)
  LOW / INFO      -> dropped (no finding)

Soft-fail when the scanner is missing: emit both envelopes with
overall_status="inapplicable" and exit 0, so check-skill remains
runnable on a fresh clone without the ~5GB scanner dependency tree.

Usage:
  check_cisco.py <SKILL.md | skills/dir | file-under-skill> [...]
  check_cisco.py --llm plugins/wiki/skills/lint/SKILL.md

Exit codes:
  0   no FAIL findings (or scanner not installed)
  1   one or more CRITICAL/HIGH findings
  64  bad arguments or --llm without API key
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

INSTALL_HINT = (
    "pip install cisco-ai-skill-scanner==2.0.9 "
    "(or: pip install --require-hashes -r .github/scripts/requirements.lock)"
)

# Severity -> (rule_id, status). LOW / INFO drop to None (no finding).
_SEVERITY_MAP: dict[str, tuple[str, str] | None] = {
    "CRITICAL": ("scanner-fail", "fail"),
    "HIGH": ("scanner-fail", "fail"),
    "MEDIUM": ("scanner-warn", "warn"),
    "LOW": None,
    "INFO": None,
}

_RULE_ORDER: list[str] = ["scanner-fail", "scanner-warn"]

_RECIPE_SCANNER_FAIL = (
    "Address the scanner-flagged CRITICAL/HIGH finding before merging. "
    "These map to prompt-injection, data-exfiltration, or supply-chain "
    "risks the cisco-ai-skill-scanner identifies as load-bearing. "
    "Consult the per-rule remediation surfaced in the finding context "
    "(or `skill-scanner` rule docs) — typical fixes are: remove the "
    "untrusted-input ingestion, scope tool permissions tighter, "
    "remove or pin the unverified external resource, or move the "
    "destructive workflow behind an explicit approval gate."
)

_RECIPE_SCANNER_WARN = (
    "Review the scanner-flagged MEDIUM finding and apply the per-rule "
    "remediation in the finding context. MEDIUM findings are coaching "
    "signals that may be load-bearing in your context — judge whether "
    "the pattern is intentional (and add a comment justifying the "
    "exception) or repair it. Consult `skill-scanner` rule docs for "
    "the canonical fix."
)

_RECIPES: dict[str, str] = {
    "scanner-fail": _RECIPE_SCANNER_FAIL,
    "scanner-warn": _RECIPE_SCANNER_WARN,
}


def _emit_inapplicable_array() -> list[dict]:
    return [
        emit_rule_envelope(rule_id=r, findings=[], inapplicable=True)
        for r in _RULE_ORDER
    ]


def discover_skill_dirs(paths: list[str]) -> list[Path]:
    """Resolve each input to its parent skill directory."""
    dirs: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            print(f"check_cisco.py: path not found: {raw}", file=sys.stderr)
            raise SystemExit(EXIT_USAGE)
        if "_shared" in p.parts:
            continue
        if p.is_file() and p.name == "SKILL.md":
            dirs.add(p.parent)
        elif p.is_dir():
            for skill_md in p.rglob("SKILL.md"):
                if "_shared" in skill_md.parts:
                    continue
                dirs.add(skill_md.parent)
        elif p.is_file():
            for parent in p.parents:
                if (parent / "SKILL.md").exists():
                    dirs.add(parent)
                    break
    return sorted(dirs)


def run_scanner(skill_dir: Path, use_llm: bool) -> dict:
    cmd = ["skill-scanner", "scan", str(skill_dir), "--format", "json"]
    if use_llm:
        cmd.append("--use-llm")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout)


def _make_finding(finding: dict, skill_dir: Path) -> dict | None:
    sev = (finding.get("severity") or "").upper()
    mapped = _SEVERITY_MAP.get(sev)
    if mapped is None:
        return None
    rule_id, status = mapped
    scanner_rule = finding.get("rule_id", "scanner")
    title = finding.get("title") or finding.get("description") or "scanner finding"
    file_rel = finding.get("file_path") or ""
    line = finding.get("line_number") or 0
    path = f"{skill_dir}/{file_rel}" if file_rel else str(skill_dir)
    context = f"[{scanner_rule}] {title}"
    if line:
        context = f"{context} (scanner line {line})"
    remediation = finding.get("remediation") or ""
    recipe = _RECIPES[rule_id]
    if remediation:
        recipe = f"{recipe}\n\nScanner remediation: {remediation}"
    return emit_json_finding(
        rule_id=rule_id,
        status=status,
        location={"line": int(line) if line else 1, "context": f"{path}: {context}"},
        reasoning=(
            f"cisco-ai-skill-scanner flagged {scanner_rule} "
            f"(severity {sev}) in {path}: {title}."
        ),
        recommended_changes=recipe,
    )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_cisco.py",
        description="Tier-1 wrapper around cisco-ai-skill-scanner.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="SKILL.md paths, skills/ directories, or files under a skill dir.",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        default=os.environ.get("SCAN_USE_LLM") == "1",
        help="Include the LLM analyzer (requires ANTHROPIC_API_KEY in env).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


def _main(argv: list[str] | None) -> int:
    args = get_parser().parse_args(argv)

    if shutil.which("skill-scanner") is None:
        print_envelope(_emit_inapplicable_array())
        print(
            f"INFO: skill-scanner not installed; install with: {INSTALL_HINT}",
            file=sys.stderr,
        )
        return 0

    if args.llm and not (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("SKILL_SCANNER_LLM_API_KEY")
    ):
        print(
            "check_cisco.py: --llm requested but ANTHROPIC_API_KEY is not set",
            file=sys.stderr,
        )
        return EXIT_USAGE

    skill_dirs = discover_skill_dirs(args.paths)
    per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}

    for skill_dir in skill_dirs:
        try:
            data = run_scanner(skill_dir, args.llm)
        except (OSError, json.JSONDecodeError) as exc:
            per_rule["scanner-warn"].append(
                emit_json_finding(
                    rule_id="scanner-warn",
                    status="warn",
                    location={
                        "line": 1,
                        "context": f"{skill_dir}: scanner invocation failed",
                    },
                    reasoning=(
                        f"skill-scanner invocation failed for {skill_dir}: "
                        f"{exc}. Re-run skill-scanner manually and inspect output."
                    ),
                    recommended_changes=_RECIPES["scanner-warn"],
                )
            )
            continue
        for finding in data.get("findings", []):
            mapped = _make_finding(finding, skill_dir)
            if mapped is None:
                continue
            per_rule[mapped["rule_id"]].append(mapped)

    envelopes = [
        emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in _RULE_ORDER
    ]
    print_envelope(envelopes)
    return 1 if any(e["overall_status"] == "fail" for e in envelopes) else 0


if __name__ == "__main__":
    sys.exit(main())
