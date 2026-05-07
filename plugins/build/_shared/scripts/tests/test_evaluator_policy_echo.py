"""Tests for check_evaluator_policy_echo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import check_evaluator_policy_echo  # noqa: E402

find_violations = check_evaluator_policy_echo.find_violations
main = check_evaluator_policy_echo.main


CITATION_ONLY = """---
name: example
description: example skill
---

# Example

## 3. Tier-2 Semantic Dimensions

Evaluator policy: see [check-skill-pattern.md §Evaluator
policy](../../_shared/references/check-skill-pattern.md#eval).
"""

ALL_THREE_SENTINELS = """---
name: example
---

# Example

## 3. Tier-2 Semantic Dimensions

#### Evaluator policy

- **Default-closed when borderline.** Ambiguous → warn.
- **Severity floor: WARN.** Tier-2 dims are coaching.
- **One finding per dimension maximum.** Highest-signal only.
"""

TWO_OF_THREE = """---
name: example
---

# Example

## 3. Tier-2 Semantic Dimensions

- **Default-closed when borderline.** When evidence is ambiguous, return `warn`.
- **Severity floor: WARN.** Coaching, not blocking.

(Third sentinel deliberately absent.)
"""

ONLY_ONE_SENTINEL = """---
name: example
---

# Example

We use a **Severity floor: WARN** policy throughout, but the rest of
the Evaluator policy is cited from check-skill-pattern.md.
"""

NO_SENTINELS = """---
name: example
---

# Example

A perfectly normal SKILL.md with no Evaluator policy at all.
"""


def test_citation_only_passes():
    assert find_violations(CITATION_ONLY) == []


def test_all_three_sentinels_flagged():
    violations = find_violations(ALL_THREE_SENTINELS)
    assert len(violations) == 3
    sentinels = {v["sentinel"] for v in violations}
    assert sentinels == {
        "Default-closed when borderline",
        "Severity floor: WARN",
        "One finding per dimension",
    }


def test_two_of_three_passes():
    """Boolean AND — partial overlap is not a violation."""
    assert find_violations(TWO_OF_THREE) == []


def test_only_one_sentinel_passes():
    assert find_violations(ONLY_ONE_SENTINEL) == []


def test_no_sentinels_passes():
    assert find_violations(NO_SENTINELS) == []


def test_violations_carry_line_numbers():
    violations = find_violations(ALL_THREE_SENTINELS)
    for v in violations:
        assert isinstance(v["line"], int)
        assert v["line"] > 0


def test_main_emits_json_array(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(ALL_THREE_SENTINELS, encoding="utf-8")
    rc = main([str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert len(parsed) == 3
    for entry in parsed:
        assert set(entry.keys()) == {"file", "line", "sentinel", "text"}


def test_main_clean_returns_zero(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(CITATION_ONLY, encoding="utf-8")
    rc = main([str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == []


def test_main_envelope_violation(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(ALL_THREE_SENTINELS, encoding="utf-8")
    rc = main(["--envelope", str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["rule_id"] == "evaluator-policy-echo"
    assert parsed["overall_status"] == "warn"
    assert len(parsed["findings"]) == 3
    for finding in parsed["findings"]:
        assert finding["status"] == "warn"
        assert "line" in finding["location"]
        assert finding["recommended_changes"]


def test_main_envelope_clean_returns_pass(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(CITATION_ONLY, encoding="utf-8")
    rc = main(["--envelope", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["rule_id"] == "evaluator-policy-echo"
    assert parsed["overall_status"] == "pass"
    assert parsed["findings"] == []


def test_main_human_output(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(ALL_THREE_SENTINELS, encoding="utf-8")
    rc = main(["--human", str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Default-closed when borderline" in captured.out
    assert str(skill) in captured.out


def test_main_two_of_three_passes(tmp_path, capsys):
    skill = tmp_path / "skill-dir" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(TWO_OF_THREE, encoding="utf-8")
    rc = main(["--envelope", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["overall_status"] == "pass"
