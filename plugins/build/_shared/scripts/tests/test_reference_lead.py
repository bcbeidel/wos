"""Tests for check_reference_lead."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import check_reference_lead  # noqa: E402

find_violation = check_reference_lead.find_violation
extract_description = check_reference_lead.extract_description
extract_lead = check_reference_lead.extract_lead
tokenize = check_reference_lead.tokenize
coverage = check_reference_lead.coverage
main = check_reference_lead.main


HIGH_OVERLAP_INLINE = """---
name: Output Discipline
description: Route data to stdout, route logs to stderr, exit non-zero via die.
paths:
  - "**/*.sh"
---

Route data to stdout, route logs to stderr, and exit non-zero via a die helper.

**Why:** stdout-for-data convention.

**How to apply:** define die.
"""

DISTINCT_LEAD = """---
name: Performance Intent
description: Replace external commands inside loops with bash builtins.
paths:
  - "**/*.sh"
---

Eliminate unnecessary subshells and prefer parameter expansion in tight code paths.

**Why:** subshells fork a process per invocation.
"""

NO_LEAD_PARAGRAPH = """---
name: Empty Lead
description: A reference whose body opens directly with Why.
---

**Why:** the description carries the imperative.

**How to apply:** start the body at Why.
"""

NO_DESCRIPTION = """---
name: Missing Description
paths:
  - "**/*.md"
---

This file restates its name in the body lead but has no description to compare against.

**Why:** without description, no overlap to compute.
"""

FOLDED_DESCRIPTION = """---
name: Folded Scalar
description: >-
  Route data to stdout and route logs to stderr,
  exiting non-zero via a die helper on errors.
paths:
  - "**/*.sh"
---

Route data to stdout, route logs to stderr, and exit non-zero via die on errors.

**Why:** convention.
"""

LITERAL_DESCRIPTION = """---
name: Literal Scalar
description: |
  Validate inputs early before destructive work.
paths:
  - "**/*.sh"
---

Validate inputs early before any destructive work begins on disk.

**Why:** destructive work is irreversible.
"""

STOPWORDS_ONLY_OVERLAP = """---
name: Stopword Overlap
description: The team will use this for that work when also needed.
---

The system can have these things from those that they use.

**Why:** stopwords carry no signal.
"""

THRESHOLD_BELOW = """---
name: Below Threshold
description: alpha bravo charlie delta echo foxtrot golf hotel india juliet
---

alpha bravo charlie delta echo foxtrot kilo lima mike november oscar papa

**Why:** 6 of 10 description tokens covered = 0.60, below threshold.
"""

THRESHOLD_BORDERLINE_PASS = """---
name: Borderline Pass
description: alpha bravo charlie delta echo foxtrot golf hotel india juliet
---

alpha bravo charlie delta echo foxtrot golf kilo lima mike november oscar

**Why:** 7 of 10 covered = 0.70.
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / "references" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def test_high_overlap_flagged():
    v = find_violation(HIGH_OVERLAP_INLINE)
    assert v is not None
    assert v["overlap"] >= 0.70
    assert "Route data to stdout" in v["lead_text"]
    assert v["lead_line_start"] == 8


def test_distinct_lead_not_flagged():
    assert find_violation(DISTINCT_LEAD) is None


def test_no_lead_paragraph_not_flagged():
    assert find_violation(NO_LEAD_PARAGRAPH) is None


def test_missing_description_not_flagged():
    assert find_violation(NO_DESCRIPTION) is None


def test_folded_description_parsed():
    desc = extract_description(
        "name: x\ndescription: >-\n  Route data to stdout and route logs to stderr,\n  "
        "exiting non-zero via a die helper on errors.\npaths:\n  - \"**/*.sh\""
    )
    assert "Route data to stdout" in desc
    assert "die helper" in desc
    v = find_violation(FOLDED_DESCRIPTION)
    assert v is not None


def test_literal_description_parsed():
    v = find_violation(LITERAL_DESCRIPTION)
    assert v is not None
    assert v["overlap"] >= 0.70


def test_stopwords_excluded():
    assert find_violation(STOPWORDS_ONLY_OVERLAP) is None


def test_threshold_boundary():
    pass_case = find_violation(THRESHOLD_BORDERLINE_PASS)
    assert pass_case is not None
    assert abs(pass_case["overlap"] - 0.70) < 0.001
    fail_case = find_violation(THRESHOLD_BELOW)
    assert fail_case is None


def test_envelope_shape(tmp_path, capsys):
    _write(tmp_path, "check-a.md", HIGH_OVERLAP_INLINE)
    rc = main(["--envelope", str(tmp_path)])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["rule_id"] == "reference-lead-echo"
    assert out["overall_status"] == "warn"
    assert len(out["findings"]) == 1
    finding = out["findings"][0]
    assert finding["status"] == "warn"
    assert "recommended_changes" in finding
    assert "location" in finding


def test_directory_walk(tmp_path, capsys):
    _write(tmp_path, "check-a.md", HIGH_OVERLAP_INLINE)
    _write(tmp_path, "check-b.md", LITERAL_DESCRIPTION)
    _write(tmp_path, "check-c.md", DISTINCT_LEAD)
    rc = main([str(tmp_path)])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 2
    files = {Path(v["file"]).name for v in out}
    assert files == {"check-a.md", "check-b.md"}


def test_clean_directory_exits_zero(tmp_path, capsys):
    _write(tmp_path, "check-a.md", DISTINCT_LEAD)
    _write(tmp_path, "check-b.md", NO_LEAD_PARAGRAPH)
    rc = main([str(tmp_path)])
    assert rc == 0


def test_extract_lead_stops_at_why():
    body = "Lead text here.\n\n**Why:** reason."
    text, start, end = extract_lead(body)
    assert text == "Lead text here."
    assert start == 1
    assert end == 1


def test_extract_lead_skips_leading_blanks():
    body = "\n\nLead text.\n"
    text, start, end = extract_lead(body)
    assert text == "Lead text."
    assert start == 3


def test_extract_lead_returns_empty_when_body_starts_with_why():
    body = "**Why:** reason."
    text, start, end = extract_lead(body)
    assert text == ""


def test_coverage_metric():
    a = {"alpha", "bravo", "charlie", "delta"}
    b = {"alpha", "bravo", "charlie", "echo", "foxtrot"}
    assert coverage(a, b) == 0.75
    assert coverage(set(), b) == 0.0


def test_only_walks_files_under_references(tmp_path, capsys):
    p = tmp_path / "not-references" / "x.md"
    p.parent.mkdir()
    p.write_text(HIGH_OVERLAP_INLINE, encoding="utf-8")
    rc = main([str(tmp_path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == []
