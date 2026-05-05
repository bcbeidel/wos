"""Tests for orchestrator.py.

Uses inline markdown strings + tmp_path fixtures to construct a mock
check-* skill. Mocks the subagent invocation function so tests run
without an API key. Stdlib + pytest only.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the script importable.
_SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPT_DIR))

import orchestrator  # noqa: E402

# ---- helpers ----------------------------------------------------------------


def _make_skill(tmp_path: Path) -> Path:
    """Create a minimal mock check-* skill with references/ and scripts/."""
    skill = tmp_path / "check-foo"
    (skill / "references").mkdir(parents=True)
    (skill / "scripts").mkdir(parents=True)
    return skill


def _write_rule(
    skill: Path, rule_id: str, sc_code: str | None = None, body: str = ""
) -> Path:
    """Write a minimal rule file with optional SC code in description."""
    desc = f"Test rule {rule_id}."
    if sc_code:
        desc += f" (shellcheck {sc_code})"
    text = (
        "---\n"
        f"name: {rule_id.title().replace('-', ' ')}\n"
        f"description: {desc}\n"
        "---\n\n"
        + (
            body
            or f"Do the {rule_id} thing.\n\n**Why:** test.\n\n**How to apply:** test.\n"
        )
    )
    path = skill / "references" / f"rule-{rule_id}.md"
    path.write_text(text)
    return path


def _write_script(skill: Path, name: str, body: str) -> Path:
    """Write an executable script (Python or Bash by suffix)."""
    path = skill / "scripts" / name
    path.write_text(body)
    path.chmod(0o755)
    return path


# ---- _derive_rule_id --------------------------------------------------------


def test_derive_rule_id_strips_prefix_and_suffix(tmp_path: Path):
    p = tmp_path / "rule-foo-bar.md"
    p.touch()
    assert orchestrator._derive_rule_id(p) == "foo-bar"


# ---- _enumerate_rules -------------------------------------------------------


def test_enumerate_rules_sorted_and_filters_non_rule_files(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "zebra")
    _write_rule(skill, "apple")
    (skill / "references" / "_hub.md").write_text("hub")
    (skill / "references" / "audit-dimensions.md").write_text("legacy")
    paths = orchestrator._enumerate_rules(skill)
    assert [p.name for p in paths] == ["rule-apple.md", "rule-zebra.md"]


def test_enumerate_rules_returns_empty_when_no_references_dir(tmp_path: Path):
    assert orchestrator._enumerate_rules(tmp_path) == []


# ---- _build_alt_id_map ------------------------------------------------------


def test_build_alt_id_map_scans_frontmatter_only(tmp_path: Path):
    """Body mentions of SC codes should NOT pollute the mapping."""
    skill = _make_skill(tmp_path)
    # Primary: SC2086 in description.
    _write_rule(skill, "primary-rule", sc_code="SC2086")
    # Sibling: SC2046 in description, but mentions SC2086 in body
    # (cross-reference).
    sibling_path = skill / "references" / "rule-sibling-rule.md"
    sibling_path.write_text(
        "---\n"
        "name: Sibling\n"
        "description: Test (shellcheck SC2046).\n"
        "---\n\n"
        "Body talks about both SC2046 and SC2086 (cross-reference).\n"
    )
    rule_paths = orchestrator._enumerate_rules(skill)
    alt_map = orchestrator._build_alt_id_map(rule_paths)
    # SC2086 should map to primary-rule, NOT sibling-rule.
    assert alt_map["SC2086"] == "primary-rule"
    assert alt_map["SC2046"] == "sibling-rule"


# ---- _classify_rules --------------------------------------------------------


def test_classify_scripted_when_rule_id_appears_in_script(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "shebang")
    _write_script(
        skill, "check_structure.py", '# emits "shebang" in findings\nprint("shebang")\n'
    )
    rule_paths = orchestrator._enumerate_rules(skill)
    alt_map = orchestrator._build_alt_id_map(rule_paths)
    classification = orchestrator._classify_rules(skill, ["shebang"], alt_map)
    assert classification == {"shebang": True}


def test_classify_scripted_via_alt_id_when_only_sc_code_in_script(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "unquoted-vars", sc_code="SC2086")
    _write_script(skill, "check_shellcheck.py", "# wraps shellcheck; emits SC2086\n")
    rule_paths = orchestrator._enumerate_rules(skill)
    alt_map = orchestrator._build_alt_id_map(rule_paths)
    classification = orchestrator._classify_rules(skill, ["unquoted-vars"], alt_map)
    assert classification == {"unquoted-vars": True}


def test_classify_judgment_when_neither_id_in_scripts(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "function-design")
    _write_script(skill, "check_other.py", "# unrelated\n")
    rule_paths = orchestrator._enumerate_rules(skill)
    alt_map = orchestrator._build_alt_id_map(rule_paths)
    classification = orchestrator._classify_rules(skill, ["function-design"], alt_map)
    assert classification == {"function-design": False}


def test_classify_judgment_when_no_scripts_dir(tmp_path: Path):
    skill = tmp_path / "check-foo"
    (skill / "references").mkdir(parents=True)
    _write_rule(skill, "anything")
    classification = orchestrator._classify_rules(skill, ["anything"], {})
    assert classification == {"anything": False}


# ---- _run_scripts (regex parsing) -------------------------------------------


def test_run_scripts_parses_lint_format_and_translates_alt_ids(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "unquoted-vars", sc_code="SC2086")
    # Bash script that always emits a fixed lint-format finding.
    _write_script(
        skill,
        "check_shellcheck.sh",
        '#!/usr/bin/env bash\necho "FAIL  $1 — SC2086: line 5: var \\$x unquoted"\n',
    )
    artifact = tmp_path / "artifact.sh"
    artifact.write_text("#!/usr/bin/env bash\nx=1\necho $x\n")
    rule_paths = orchestrator._enumerate_rules(skill)
    alt_map = orchestrator._build_alt_id_map(rule_paths)
    findings = orchestrator._run_scripts(skill, artifact, alt_map)
    # SC2086 should be translated to canonical "unquoted-vars".
    assert "unquoted-vars" in findings
    assert findings["unquoted-vars"][0]["severity"] == "FAIL"
    assert findings["unquoted-vars"][0]["location"]["line"] == 5


def test_run_scripts_ignores_non_finding_lines(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "thing")
    _write_script(
        skill,
        "check_thing.sh",
        '#!/usr/bin/env bash\necho "starting check..."\necho "done"\nexit 0\n',
    )
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    findings = orchestrator._run_scripts(skill, artifact, {})
    assert findings == {}


# ---- audit (full integration with mocked subagent) --------------------------


class _FakeSubagent:
    """Records calls; returns canned responses."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, rule_md, artifact, findings=None):
        self.calls.append(
            {"findings": findings, "rule_md_first_line": rule_md.split("\n")[1]}
        )
        if findings:
            return {"rule_id": "x", "overall_status": "fail", "findings": findings}
        return {"rule_id": "x", "overall_status": "pass", "findings": []}


def test_audit_skips_subagent_when_scripted_and_no_findings(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "shebang")
    _write_script(
        skill,
        "check_structure.sh",
        "#!/usr/bin/env bash\n# mentions shebang; exits clean\nexit 0\n",
    )
    artifact = tmp_path / "artifact.sh"
    artifact.write_text("#!/usr/bin/env bash\n")
    fake = _FakeSubagent()
    results = orchestrator.audit(skill, artifact, invoke_fn=fake)
    assert len(results) == 1
    assert results[0]["mode"] == "skipped-no-script-findings"
    assert results[0]["overall_status"] == "pass"
    assert fake.calls == []


def test_audit_invokes_subagent_in_recipe_mode_when_script_fires(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "shebang")
    _write_script(
        skill,
        "check_structure.sh",
        '#!/usr/bin/env bash\necho "FAIL  $1 — shebang: bad"\nexit 1\n',
    )
    artifact = tmp_path / "artifact.sh"
    artifact.write_text("contents")
    fake = _FakeSubagent()
    results = orchestrator.audit(skill, artifact, invoke_fn=fake)
    assert results[0]["mode"] == "recipe"
    assert len(fake.calls) == 1
    assert fake.calls[0]["findings"] is not None
    assert fake.calls[0]["findings"][0]["severity"] == "FAIL"


def test_audit_invokes_subagent_in_judgment_mode_for_unscripted_rule(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "function-design")
    # Script content must NOT contain the literal string "function-design"
    # (would trigger scripted classification via the substring grep).
    _write_script(skill, "check_unrelated.py", "# placeholder; emits other ids\n")
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    fake = _FakeSubagent()
    results = orchestrator.audit(skill, artifact, invoke_fn=fake)
    assert results[0]["mode"] == "judgment"
    assert len(fake.calls) == 1
    assert fake.calls[0]["findings"] is None


def test_audit_filters_to_specified_rules(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "alpha")
    _write_rule(skill, "beta")
    _write_rule(skill, "gamma")
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    fake = _FakeSubagent()
    results = orchestrator.audit(skill, artifact, rules_filter=["beta"], invoke_fn=fake)
    assert [r["mode"] for r in results] == ["judgment"]
    assert len(fake.calls) == 1


# ---- main / argparse / dry-run ---------------------------------------------


def test_main_dry_run_emits_classification_plan(tmp_path: Path, capsys):
    skill = _make_skill(tmp_path)
    _write_rule(skill, "alpha")
    _write_rule(skill, "beta", sc_code="SC1234")
    _write_script(skill, "check_alpha.sh", "#!/usr/bin/env bash\n# alpha\nexit 0\n")
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    rc = orchestrator.main(
        [
            "--skill-dir",
            str(skill),
            "--artifact-file",
            str(artifact),
            "--dry-run",
        ]
    )
    assert rc == 0
    import json as _json

    data = _json.loads(capsys.readouterr().out)
    assert data["rule_count"] == 2
    by_id = {e["rule_id"]: e for e in data["plan"]}
    assert by_id["alpha"]["scripted"] is True
    assert by_id["beta"]["scripted"] is False  # SC1234 not in any script


def test_main_missing_skill_dir_returns_usage_error(tmp_path: Path, capsys):
    rc = orchestrator.main(
        [
            "--skill-dir",
            str(tmp_path / "nonexistent"),
            "--artifact-file",
            str(tmp_path / "x"),
            "--dry-run",
        ]
    )
    assert rc == orchestrator.EXIT_USAGE
    assert "skill dir not found" in capsys.readouterr().err
