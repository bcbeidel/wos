from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import _common  # noqa: E402

# ---- emit_json_finding -----------------------------------------------------


def test_emit_json_finding_returns_complete_dict():
    f = _common.emit_json_finding(
        rule_id="shebang",
        status="fail",
        location={"line": 1, "context": "#!/bin/sh"},
        reasoning="First line is /bin/sh, not bash.",
        recommended_changes="Replace with `#!/usr/bin/env bash`.",
    )
    assert f == {
        "rule_id": "shebang",
        "status": "fail",
        "location": {"line": 1, "context": "#!/bin/sh"},
        "reasoning": "First line is /bin/sh, not bash.",
        "recommended_changes": "Replace with `#!/usr/bin/env bash`.",
    }


def test_emit_json_finding_accepts_warn_status():
    f = _common.emit_json_finding(
        rule_id="line-length",
        status="warn",
        location={"line": 42, "context": "..." * 40},
        reasoning="Line exceeds 100 chars.",
        recommended_changes="Break with `\\` continuation.",
    )
    assert f["status"] == "warn"


def test_emit_json_finding_rejects_invalid_status():
    with pytest.raises(ValueError, match="status must be one of"):
        _common.emit_json_finding(
            rule_id="x",
            status="info",  # not allowed at finding level
            location=None,
            reasoning="r",
            recommended_changes="fix",
        )


def test_emit_json_finding_rejects_empty_recommended_changes():
    with pytest.raises(ValueError, match="recommended_changes is required"):
        _common.emit_json_finding(
            rule_id="x",
            status="fail",
            location=None,
            reasoning="r",
            recommended_changes="",
        )


def test_emit_json_finding_rejects_whitespace_only_recommended_changes():
    with pytest.raises(ValueError, match="recommended_changes is required"):
        _common.emit_json_finding(
            rule_id="x",
            status="fail",
            location=None,
            reasoning="r",
            recommended_changes="   \n  ",
        )


def test_emit_json_finding_accepts_null_location():
    f = _common.emit_json_finding(
        rule_id="size",
        status="warn",
        location=None,
        reasoning="Whole-file violation.",
        recommended_changes="Split into _lib_*.sh helpers.",
    )
    assert f["location"] is None


# ---- emit_rule_envelope ----------------------------------------------------


def test_emit_rule_envelope_pass_when_no_findings():
    env = _common.emit_rule_envelope(rule_id="shebang", findings=[])
    assert env == {"rule_id": "shebang", "overall_status": "pass", "findings": []}


def test_emit_rule_envelope_warn_when_only_warn_findings():
    findings = [{"status": "warn"}, {"status": "warn"}]
    env = _common.emit_rule_envelope(rule_id="line-length", findings=findings)
    assert env["overall_status"] == "warn"


def test_emit_rule_envelope_fail_when_any_fail_finding():
    findings = [{"status": "warn"}, {"status": "fail"}, {"status": "warn"}]
    env = _common.emit_rule_envelope(rule_id="secret", findings=findings)
    assert env["overall_status"] == "fail"


def test_emit_rule_envelope_inapplicable_overrides_findings():
    findings = [{"status": "fail"}]
    env = _common.emit_rule_envelope(
        rule_id="cross-entity-collision", findings=findings, inapplicable=True
    )
    assert env["overall_status"] == "inapplicable"


def test_emit_rule_envelope_includes_findings_list():
    f = {
        "status": "fail",
        "location": None,
        "reasoning": "r",
        "recommended_changes": "x",
    }
    env = _common.emit_rule_envelope(rule_id="r", findings=[f])
    assert env["findings"] == [f]


# ---- print_envelope --------------------------------------------------------


def test_print_envelope_emits_indented_json(capsys):
    env = _common.emit_rule_envelope(
        rule_id="r",
        findings=[
            _common.emit_json_finding(
                rule_id="r",
                status="warn",
                location=None,
                reasoning="r",
                recommended_changes="fix",
            )
        ],
    )
    _common.print_envelope(env)
    out = capsys.readouterr().out
    assert '"rule_id": "r"' in out
    assert '"overall_status": "warn"' in out
    assert out.endswith("\n")


def test_print_envelope_accepts_array():
    arr = [
        _common.emit_rule_envelope(rule_id="a", findings=[]),
        _common.emit_rule_envelope(rule_id="b", findings=[]),
    ]
    import io
    import json

    # Round-trip through stdout capture is sufficient
    captured = io.StringIO()
    import sys as _sys

    saved = _sys.stdout
    _sys.stdout = captured
    try:
        _common.print_envelope(arr)
    finally:
        _sys.stdout = saved
    parsed = json.loads(captured.getvalue())
    assert isinstance(parsed, list)
    assert [e["rule_id"] for e in parsed] == ["a", "b"]
