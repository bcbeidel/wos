"""Tests for orchestrator.py — union-discovery model.

Inline markdown strings + tmp_path fixtures. Mocks the subagent invocation
function so tests run without an API key. Stdlib + pytest only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

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


def _write_judgment_rule(skill: Path, rule_id: str, body: str = "") -> Path:
    """Write a judgment-mode rule at references/check-<rule_id>.md."""
    text = (
        "---\n"
        f"name: {rule_id.title().replace('-', ' ')}\n"
        f"description: Test rule {rule_id}.\n"
        "---\n\n"
        + (
            body
            or f"Do the {rule_id} thing.\n\n**Why:** test.\n\n**How to apply:** test.\n"
        )
    )
    path = skill / "references" / f"check-{rule_id}.md"
    path.write_text(text)
    return path


def _write_script(skill: Path, name: str, body: str) -> Path:
    """Write an executable script (Python or Bash by suffix)."""
    path = skill / "scripts" / name
    path.write_text(body)
    path.chmod(0o755)
    return path


def _emit_envelope_script(rule_id: str, status: str = "pass") -> str:
    """Bash one-liner script body that emits a JSON envelope to stdout."""
    return (
        "#!/usr/bin/env bash\n"
        "cat <<JSON\n"
        "{"
        f' "rule_id": "{rule_id}", '
        f'"overall_status": "{status}", '
        '"findings": []'
        "}\n"
        "JSON\n"
    )


def _emit_array_script(rule_ids: list[str]) -> str:
    """Bash script body that emits a JSON array of empty-pass envelopes."""
    items = ",".join(
        f'{{"rule_id": "{r}", "overall_status": "pass", "findings": []}}'
        for r in rule_ids
    )
    return (
        "#!/usr/bin/env bash\n"
        "cat <<JSON\n"
        f"[{items}]\n"
        "JSON\n"
    )


# ---- _derive_rule_id --------------------------------------------------------


def test_derive_rule_id_strips_check_prefix(tmp_path: Path):
    p = tmp_path / "check-foo-bar.md"
    p.touch()
    assert orchestrator._derive_rule_id(p) == "foo-bar"


def test_derive_rule_id_strips_legacy_rule_prefix(tmp_path: Path):
    p = tmp_path / "rule-baz.md"
    p.touch()
    assert orchestrator._derive_rule_id(p) == "baz"


# ---- _enumerate_judgment_rules ---------------------------------------------


def test_enumerate_judgment_rules_globs_check_md(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_judgment_rule(skill, "zebra")
    _write_judgment_rule(skill, "apple")
    # Non-rule files are filtered out.
    (skill / "references" / "audit-dimensions.md").write_text("legacy")
    (skill / "references" / "rule-old.md").write_text("legacy rule prefix")
    paths = orchestrator._enumerate_judgment_rules(skill)
    assert [p.name for p in paths] == ["check-apple.md", "check-zebra.md"]


def test_enumerate_judgment_rules_returns_empty_when_no_references_dir(tmp_path: Path):
    assert orchestrator._enumerate_judgment_rules(tmp_path) == []


# ---- _run_one_script --------------------------------------------------------


def test_run_one_script_parses_single_envelope(tmp_path: Path):
    skill = _make_skill(tmp_path)
    s = _write_script(skill, "check_foo.sh", _emit_envelope_script("foo"))
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    envelopes = orchestrator._run_one_script(s, artifact)
    assert envelopes == [{"rule_id": "foo", "overall_status": "pass", "findings": []}]


def test_run_one_script_parses_array(tmp_path: Path):
    skill = _make_skill(tmp_path)
    s = _write_script(skill, "check_multi.sh", _emit_array_script(["a", "b", "c"]))
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    envelopes = orchestrator._run_one_script(s, artifact)
    assert [e["rule_id"] for e in envelopes] == ["a", "b", "c"]


def test_run_one_script_returns_empty_on_malformed_json(tmp_path: Path):
    skill = _make_skill(tmp_path)
    s = _write_script(
        skill, "check_broken.sh", '#!/usr/bin/env bash\necho "not json"\n'
    )
    artifact = tmp_path / "artifact"
    artifact.write_text("x")
    assert orchestrator._run_one_script(s, artifact) == []


def test_run_one_script_returns_empty_on_empty_output(tmp_path: Path):
    skill = _make_skill(tmp_path)
    s = _write_script(skill, "check_silent.sh", "#!/usr/bin/env bash\nexit 0\n")
    artifact = tmp_path / "artifact"
    artifact.write_text("x")
    assert orchestrator._run_one_script(s, artifact) == []


# ---- _run_all_scripts -------------------------------------------------------


def test_run_all_scripts_collects_rule_ids_to_envelopes(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_script(skill, "check_one.sh", _emit_envelope_script("alpha"))
    _write_script(skill, "check_two.sh", _emit_array_script(["beta", "gamma"]))
    artifact = tmp_path / "artifact"
    artifact.write_text("x")
    envs = orchestrator._run_all_scripts(skill, artifact)
    assert sorted(envs.keys()) == ["alpha", "beta", "gamma"]


# ---- audit (full integration with mocked subagent) --------------------------


class _FakeSubagent:
    """Records calls; returns a canned judgment-mode response.

    Crucially: this fake mimics the post-Task-14 signature
    `invoke_subagent(rule_md, artifact)` — no `findings` parameter.
    """

    def __init__(self, returned_rule_id: str = "DRIFT"):
        self.calls: list[dict] = []
        self.returned_rule_id = returned_rule_id

    def __call__(self, rule_md, artifact):
        self.calls.append({"rule_md_first_line": rule_md.split("\n")[1]})
        # Simulate model drift: subagent returns a wrong rule_id.
        return {
            "rule_id": self.returned_rule_id,
            "overall_status": "warn",
            "findings": [],
        }


def test_audit_scripted_rule_passes_through_envelope(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_script(skill, "check_foo.sh", _emit_envelope_script("foo", status="warn"))
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    fake = _FakeSubagent()
    results = orchestrator.audit(skill, artifact, invoke_fn=fake)
    assert len(results) == 1
    assert results[0]["rule_id"] == "foo"
    assert results[0]["mode"] == "scripted"
    assert results[0]["overall_status"] == "warn"
    assert fake.calls == []  # No subagent call for scripted rules.


def test_audit_judgment_rule_invokes_subagent_no_findings_arg(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_judgment_rule(skill, "function-design")
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    fake = _FakeSubagent()
    results = orchestrator.audit(skill, artifact, invoke_fn=fake)
    assert results[0]["mode"] == "judgment"
    assert len(fake.calls) == 1


def test_audit_overrides_model_emitted_rule_id_with_filename_derived(tmp_path: Path):
    """Defensive against the live-smoke drift bug.

    Subagent returned `subprocess-and-tool-hygiene` (model invented an
    'and') when the canonical rule_id was `subprocess-tool-hygiene`.
    Orchestrator overrides the result's rule_id with the filename-derived
    one.
    """
    skill = _make_skill(tmp_path)
    _write_judgment_rule(skill, "output-discipline")
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    fake = _FakeSubagent(returned_rule_id="output_discipline_DRIFT")
    results = orchestrator.audit(skill, artifact, invoke_fn=fake)
    assert results[0]["rule_id"] == "output-discipline"  # overridden
    assert results[0]["mode"] == "judgment"


def test_audit_overlap_raises_value_error(tmp_path: Path):
    """A rule_id present in BOTH judgment .md and a script's output is illegal."""
    skill = _make_skill(tmp_path)
    _write_judgment_rule(skill, "shebang")
    _write_script(skill, "check_structure.sh", _emit_envelope_script("shebang"))
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    fake = _FakeSubagent()
    with pytest.raises(ValueError, match="Single-artifact-per-rule violation"):
        orchestrator.audit(skill, artifact, invoke_fn=fake)


def test_audit_filters_to_specified_rules(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_judgment_rule(skill, "alpha")
    _write_judgment_rule(skill, "beta")
    _write_script(skill, "check_gamma.sh", _emit_envelope_script("gamma"))
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    fake = _FakeSubagent()
    results = orchestrator.audit(
        skill, artifact, rules_filter=["beta", "gamma"], invoke_fn=fake
    )
    rids = {r["rule_id"] for r in results}
    assert rids == {"beta", "gamma"}
    assert len(fake.calls) == 1  # only beta invoked judgment-mode


def test_audit_union_discovery_combines_judgment_and_scripted(tmp_path: Path):
    skill = _make_skill(tmp_path)
    _write_judgment_rule(skill, "j-rule")
    _write_script(skill, "check_s.sh", _emit_envelope_script("s-rule"))
    artifact = tmp_path / "artifact"
    artifact.write_text("contents")
    fake = _FakeSubagent()
    results = orchestrator.audit(skill, artifact, invoke_fn=fake)
    modes = {r["rule_id"]: r["mode"] for r in results}
    assert modes == {"j-rule": "judgment", "s-rule": "scripted"}


# ---- main / argparse / dry-run ---------------------------------------------


def test_main_dry_run_emits_classification_plan(tmp_path: Path, capsys):
    skill = _make_skill(tmp_path)
    _write_judgment_rule(skill, "alpha-judgment")
    _write_script(skill, "check_beta.sh", _emit_envelope_script("beta"))
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
    data = json.loads(capsys.readouterr().out)
    assert data["judgment_rule_count"] == 1
    assert data["scripted_rule_count"] == 1
    assert data["rule_count"] == 2
    assert data["overlap"] == []
    by_id = {e["rule_id"]: e for e in data["plan"]}
    assert by_id["alpha-judgment"]["mode"] == "judgment"
    assert by_id["beta"]["mode"] == "scripted"


def test_main_dry_run_reports_overlap_in_plan(tmp_path: Path, capsys):
    skill = _make_skill(tmp_path)
    _write_judgment_rule(skill, "shebang")
    _write_script(skill, "check_structure.sh", _emit_envelope_script("shebang"))
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
    data = json.loads(capsys.readouterr().out)
    assert "shebang" in data["overlap"]


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
