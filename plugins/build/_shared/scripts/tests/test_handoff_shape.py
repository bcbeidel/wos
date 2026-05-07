"""Tests for check_handoff_shape."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import check_handoff_shape  # noqa: E402

find_violations = check_handoff_shape.find_violations
main = check_handoff_shape.main


CLEAN_HANDOFF = """---
name: example
description: example skill
---

# Example

Body content.

## Handoff

**Chainable to:** `/build:check-skill`
"""

RECEIVES_VIOLATION = """---
name: example
---

# Example

## Handoff

**Receives:** A topic to explore
**Chainable to:** plan-work
"""

PRODUCES_VIOLATION = """---
name: example
---

# Example

## Handoff

**Produces:** A design document
**Chainable to:** plan-work
"""

BOTH_VIOLATIONS = """---
name: example
---

# Example

## Handoff

**Receives:** A topic to explore
**Produces:** A design document
**Chainable to:** plan-work
"""

NO_HANDOFF_SECTION = """---
name: example
---

# Example

## Steps

1. Do thing.

## Output Format

Some format.
"""

RECEIVES_OUTSIDE_HANDOFF = """---
name: example
---

# Example

## Steps

**Receives:** described in Step 1 below — this is body prose, not a handoff field.

## Handoff

**Chainable to:** plan-work
"""

HANDOFF_WITH_TRAILING_SECTION = """---
name: example
---

# Example

## Handoff

**Receives:** something
**Chainable to:** plan-work

## Notes

Trailing section.
"""


def test_clean_handoff_has_no_violations():
    assert find_violations(CLEAN_HANDOFF) == []


def test_receives_inside_handoff_is_flagged():
    violations = find_violations(RECEIVES_VIOLATION)
    assert len(violations) == 1
    assert violations[0]["kind"] == "receives"
    assert violations[0]["text"].startswith("**Receives:**")


def test_produces_inside_handoff_is_flagged():
    violations = find_violations(PRODUCES_VIOLATION)
    assert len(violations) == 1
    assert violations[0]["kind"] == "produces"


def test_both_receives_and_produces_flagged():
    violations = find_violations(BOTH_VIOLATIONS)
    kinds = sorted(v["kind"] for v in violations)
    assert kinds == ["produces", "receives"]


def test_file_without_handoff_section_clean():
    assert find_violations(NO_HANDOFF_SECTION) == []


def test_receives_outside_handoff_section_clean():
    assert find_violations(RECEIVES_OUTSIDE_HANDOFF) == []


def test_handoff_section_bounded_by_next_h2():
    # Receives is inside Handoff but a later H2 follows — only the Handoff
    # one should be flagged. Confirms section is bounded by next H2.
    violations = find_violations(HANDOFF_WITH_TRAILING_SECTION)
    assert len(violations) == 1
    assert violations[0]["kind"] == "receives"


def test_violations_carry_line_numbers():
    violations = find_violations(BOTH_VIOLATIONS)
    for v in violations:
        assert isinstance(v["line"], int)
        assert v["line"] > 0


def test_main_emits_json_envelope(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(BOTH_VIOLATIONS, encoding="utf-8")
    rc = main([str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    for entry in parsed:
        assert set(entry.keys()) == {"file", "line", "kind", "text"}


def test_main_clean_repo_returns_zero(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(CLEAN_HANDOFF, encoding="utf-8")
    rc = main([str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == []


def test_main_envelope_output(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(BOTH_VIOLATIONS, encoding="utf-8")
    rc = main(["--envelope", str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["rule_id"] == "handoff-shape"
    assert parsed["overall_status"] == "warn"
    assert len(parsed["findings"]) == 2
    for finding in parsed["findings"]:
        assert finding["status"] == "warn"
        assert "line" in finding["location"]
        assert finding["recommended_changes"]


def test_main_envelope_clean_returns_pass(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(CLEAN_HANDOFF, encoding="utf-8")
    rc = main(["--envelope", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["rule_id"] == "handoff-shape"
    assert parsed["overall_status"] == "pass"
    assert parsed["findings"] == []


def test_main_human_output(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(RECEIVES_VIOLATION, encoding="utf-8")
    rc = main(["--human", str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "receives:" in captured.out
    assert str(skill) in captured.out
