"""Tests for invoke_subagent.py.

Uses inline markdown strings + tmp_path fixtures. Mocks the Anthropic client
so tests run without an API key. Stdlib + pytest only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Make the script importable.
_SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPT_DIR))

import invoke_subagent  # noqa: E402

RULE_MD = """---
name: Test Rule
description: A test rule for unit tests.
paths:
  - "**/*.test"
---

Do the test thing.

**Why:** because tests need a stable rule shape to exercise the wrapper.

**How to apply:** mark every .test file as following the test thing.

**Exception:** none.
"""

ARTIFACT = "fake artifact content\nline 2 of fake content\n"


# ---- _derive_rule_id ---------------------------------------------------------


def test_derive_rule_id_from_frontmatter_name():
    rid = invoke_subagent._derive_rule_id(RULE_MD)
    assert rid == "test-rule"


def test_derive_rule_id_falls_back_to_filename(tmp_path: Path):
    rule_path = tmp_path / "rule-no-frontmatter-name.md"
    rule_path.write_text("---\ndescription: x\n---\n\nbody\n")
    rid = invoke_subagent._derive_rule_id(
        rule_path.read_text(), fallback=str(rule_path)
    )
    assert rid == "no-frontmatter-name"


# ---- _build_request ----------------------------------------------------------


def test_build_request_judgment_mode_has_three_user_blocks():
    req = invoke_subagent._build_request(
        RULE_MD, ARTIFACT, findings=None, model="test-model"
    )
    assert req["model"] == "test-model"
    assert req["tool_choice"]["name"] == "report_audit_finding"
    user_blocks = req["messages"][0]["content"]
    assert len(user_blocks) == 3
    assert "## Rule" in user_blocks[0]["text"]
    assert "## Artifact" in user_blocks[1]["text"]
    assert "judgment mode" in user_blocks[2]["text"]


def test_build_request_recipe_mode_includes_findings():
    findings = [{"location": {"line": 5, "context": "echo bad"}, "rule_id": "x"}]
    req = invoke_subagent._build_request(
        RULE_MD, ARTIFACT, findings=findings, model="test-model"
    )
    user_blocks = req["messages"][0]["content"]
    assert "Findings (recipe mode)" in user_blocks[2]["text"]
    assert "echo bad" in user_blocks[2]["text"]


def test_build_request_marks_system_and_rule_cache():
    req = invoke_subagent._build_request(
        RULE_MD, ARTIFACT, findings=None, model="test-model"
    )
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    rule_block = req["messages"][0]["content"][0]
    assert rule_block["cache_control"] == {"type": "ephemeral"}


def test_build_request_includes_tool_definition():
    req = invoke_subagent._build_request(
        RULE_MD, ARTIFACT, findings=None, model="test-model"
    )
    assert len(req["tools"]) == 1
    tool = req["tools"][0]
    assert tool["name"] == "report_audit_finding"
    assert "rule_id" in tool["input_schema"]["properties"]
    assert tool["input_schema"]["properties"]["overall_status"]["enum"] == [
        "pass",
        "warn",
        "fail",
        "inapplicable",
    ]


# ---- invoke_subagent (mocked) ------------------------------------------------


class MockClient:
    """Minimal Anthropic client mock. Returns whatever is queued."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _tool_use_response(
    rule_id: str, status: str, findings: list[dict] | None = None
) -> SimpleNamespace:
    """Construct a SimpleNamespace mimicking the Anthropic Message response."""
    tool_block = SimpleNamespace(
        type="tool_use",
        name="report_audit_finding",
        input={
            "rule_id": rule_id,
            "overall_status": status,
            "findings": findings or [],
        },
    )
    return SimpleNamespace(content=[tool_block])


def _text_only_response(text: str) -> SimpleNamespace:
    text_block = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(content=[text_block])


def test_invoke_subagent_returns_tool_input():
    client = MockClient([_tool_use_response("test-rule", "pass")])
    result = invoke_subagent.invoke_subagent(
        RULE_MD, ARTIFACT, findings=None, client=client
    )
    assert result == {"rule_id": "test-rule", "overall_status": "pass", "findings": []}
    assert len(client.calls) == 1


def test_invoke_subagent_retries_once_on_text_only():
    client = MockClient(
        [
            _text_only_response("Sorry, I cannot answer."),
            _tool_use_response(
                "test-rule", "fail", [{"status": "fail", "reasoning": "x"}]
            ),
        ]
    )
    result = invoke_subagent.invoke_subagent(
        RULE_MD, ARTIFACT, findings=None, client=client
    )
    assert result["overall_status"] == "fail"
    assert len(client.calls) == 2
    # Retry must include the corrective user message.
    last_messages = client.calls[1]["messages"]
    assert last_messages[-1]["role"] == "user"
    assert "did not call" in last_messages[-1]["content"]


def test_invoke_subagent_coerces_string_findings_to_list():
    """When the model serializes findings as a JSON string, coerce it to a list."""
    findings_as_string = json.dumps(
        [{"status": "fail", "reasoning": "x", "recommended_changes": "y"}]
    )
    tool_block = SimpleNamespace(
        type="tool_use",
        name="report_audit_finding",
        input={
            "rule_id": "test-rule",
            "overall_status": "fail",
            "findings": findings_as_string,  # string, not list
        },
    )
    response = SimpleNamespace(content=[tool_block])
    client = MockClient([response])
    result = invoke_subagent.invoke_subagent(
        RULE_MD, ARTIFACT, findings=None, client=client
    )
    assert isinstance(result["findings"], list)
    assert len(result["findings"]) == 1
    assert result["findings"][0]["status"] == "fail"


def test_invoke_subagent_leaves_malformed_string_findings_as_is():
    """Unparseable string findings stay as string; don't drop the data."""
    tool_block = SimpleNamespace(
        type="tool_use",
        name="report_audit_finding",
        input={
            "rule_id": "test-rule",
            "overall_status": "fail",
            "findings": "[malformed json {",
        },
    )
    response = SimpleNamespace(content=[tool_block])
    client = MockClient([response])
    result = invoke_subagent.invoke_subagent(
        RULE_MD, ARTIFACT, findings=None, client=client
    )
    assert result["findings"] == "[malformed json {"


def test_invoke_subagent_raises_after_two_text_only_responses():
    client = MockClient(
        [
            _text_only_response("first refusal"),
            _text_only_response("second refusal"),
        ]
    )
    with pytest.raises(invoke_subagent.SubagentToolCallError, match="after one retry"):
        invoke_subagent.invoke_subagent(RULE_MD, ARTIFACT, findings=None, client=client)
    assert len(client.calls) == 2


# ---- main / argparse / dry-run ----------------------------------------------


def test_main_dry_run_emits_request_json(tmp_path: Path, capsys):
    rule = tmp_path / "rule-test-rule.md"
    rule.write_text(RULE_MD)
    artifact = tmp_path / "artifact.test"
    artifact.write_text(ARTIFACT)

    rc = invoke_subagent.main(
        [
            "--rule-file",
            str(rule),
            "--artifact-file",
            str(artifact),
            "--dry-run",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["tool_choice"]["name"] == "report_audit_finding"


def test_main_missing_file_returns_usage_error(tmp_path: Path, capsys):
    rc = invoke_subagent.main(
        [
            "--rule-file",
            str(tmp_path / "does-not-exist.md"),
            "--artifact-file",
            str(tmp_path / "also-not-there"),
            "--dry-run",
        ]
    )
    assert rc == invoke_subagent.EXIT_USAGE
    err = capsys.readouterr().err
    assert "rule file not found" in err
