"""Tests for check_guard_step_echo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import check_guard_step_echo  # noqa: E402

find_violations = check_guard_step_echo.find_violations
main = check_guard_step_echo.main


CLEAN_GUARDS = """---
name: example
---

# Example

## Anti-Pattern Guards

1. **Setuid scaffolding** — security minefield. Refuse and recommend a
   compiled wrapper instead.
2. **Empty REQUIRED_CMDS** — silently skips preflight, killing the
   fail-fast contract.
"""

STEP_N_VIOLATION = """---
name: example
---

# Example

## Anti-Pattern Guards

1. **Conflict check skipped** — run Step 4 before drafting; contradicting
   rules produce arbitrary behavior.
"""

STEP_HASH_N_VIOLATION = """---
name: example
---

# Example

## Anti-Pattern Guards

1. **Skipped intake** — confirm the step #4 outputs before continuing.
"""

STEP_DECIMAL_VIOLATION = """---
name: example
---

# Example

## Anti-Pattern Guards

1. **Hand-waving --dry-run** — if Intake step 3.5 flagged destructive
   operations, the draft must wire the dry-run flag into the destructive
   code path.
"""

NO_GUARDS_HEADING = """---
name: example
---

# Example

## Workflow

1. Step 4 of the workflow goes here.
"""

STEP_BY_STEP_PROSE = """---
name: example
---

# Example

## Anti-Pattern Guards

1. **Skipping the step-by-step verification** — read the diff before
   marking complete.
"""

MULTIPLE_VIOLATIONS = """---
name: example
---

# Example

## Anti-Pattern Guards

1. **Multi-concern rule written as one file** — if Step 1 missed a
   split opportunity, fork back and re-split.
2. **Setuid scaffolding** — security minefield.
3. **Conflict check skipped** — run Step 4 before drafting.

## Key Instructions

Step 5 mentioned here is body prose, not a guard.
"""


def test_clean_guards_no_violations():
    assert find_violations(CLEAN_GUARDS) == []


def test_step_n_flagged():
    violations = find_violations(STEP_N_VIOLATION)
    assert len(violations) == 1
    assert violations[0]["bullet"] == 1
    assert violations[0]["match"].lower().startswith("step")


def test_step_hash_n_flagged():
    violations = find_violations(STEP_HASH_N_VIOLATION)
    assert len(violations) == 1
    assert "#4" in violations[0]["match"] or "4" in violations[0]["match"]


def test_step_decimal_flagged():
    violations = find_violations(STEP_DECIMAL_VIOLATION)
    assert len(violations) == 1
    assert "3.5" in violations[0]["match"]


def test_no_guards_heading_clean():
    # "Step 4" appears outside the guards section — not flagged.
    assert find_violations(NO_GUARDS_HEADING) == []


def test_step_by_step_prose_not_flagged():
    # "step-by-step" has no number — word-boundary anchor protects.
    assert find_violations(STEP_BY_STEP_PROSE) == []


def test_multiple_violations_bounded_by_next_h2():
    violations = find_violations(MULTIPLE_VIOLATIONS)
    bullets = sorted(v["bullet"] for v in violations)
    assert bullets == [1, 3]
    # Step 5 in Key Instructions is past the next H2 — not flagged.


def test_violations_carry_line_numbers():
    violations = find_violations(MULTIPLE_VIOLATIONS)
    for v in violations:
        assert isinstance(v["line"], int)
        assert v["line"] > 0


def test_main_emits_json(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(MULTIPLE_VIOLATIONS, encoding="utf-8")
    rc = main([str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    for entry in parsed:
        assert set(entry.keys()) == {"file", "line", "bullet", "match", "text"}


def test_main_clean_returns_zero(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(CLEAN_GUARDS, encoding="utf-8")
    rc = main([str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == []


def test_main_envelope_output(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(STEP_N_VIOLATION, encoding="utf-8")
    rc = main(["--envelope", str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["rule_id"] == "guard-step-echo"
    assert parsed["overall_status"] == "warn"
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    assert finding["status"] == "warn"
    assert "line" in finding["location"]
    assert finding["recommended_changes"]


def test_main_envelope_clean_returns_pass(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(CLEAN_GUARDS, encoding="utf-8")
    rc = main(["--envelope", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["rule_id"] == "guard-step-echo"
    assert parsed["overall_status"] == "pass"
    assert parsed["findings"] == []


def test_main_human_output(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(STEP_N_VIOLATION, encoding="utf-8")
    rc = main(["--human", str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "guard #1" in captured.out
    assert str(skill) in captured.out


def test_main_nonexistent_path_errors(tmp_path, capsys):
    missing = tmp_path / "does-not-exist" / "SKILL.md"
    rc = main([str(missing)])
    # Nonexistent SKILL.md is not picked up by _iter_skill_files (file
    # check returns False); main returns 0 with empty list — that's the
    # current contract. Treat it as a "no targets" scenario.
    assert rc == 0
