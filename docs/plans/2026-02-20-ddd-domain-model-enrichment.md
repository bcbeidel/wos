# DDD Domain Model Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Absorb helper modules into domain objects, add `auto_fix()` / `validate_content()` to document subclasses, create new domain objects (AgentsMd, ClaudeMd, RulesFile, CommunicationPreferences), and introduce the ProjectContext aggregate root.

**Architecture:** Bottom-up enrichment — enrich existing leaf objects first (ValidationIssue, document subclasses), then composites (ContextArea), then new domain objects, then the ProjectContext aggregate root. Each task is independently testable.

**Tech Stack:** Python 3.9, Pydantic v2, pytest. `from __future__ import annotations` everywhere. Tests use inline markdown strings and `tests/builders.py`.

**Important context:**
- Design doc: `docs/plans/2026-02-20-ddd-domain-model-enrichment-design.md`
- CLAUDE.md documents the DDD protocol — read it before starting
- Working directory: `/Users/bbeidel/Documents/GitHub/work-os/.worktrees/phase-ddd-enrichment`
- Branch: `phase/ddd-domain-model-enrichment`
- Run tests: `python3 -m pytest tests/ -v`
- All 583 tests currently pass

---

## Phase A: Absorb into Existing Objects ✅ COMPLETE

### Task 1: Add `requires_llm` field to ValidationIssue ✅

**Files:**
- Modify: `wos/models/validation_issue.py`
- Modify: `tests/models/test_validation_issue.py`

**Step 1: Write the failing test**

Add to `tests/models/test_validation_issue.py`:

```python
def test_requires_llm_default_false():
    issue = make_validation_issue()
    assert issue.requires_llm is False

def test_requires_llm_explicit_true():
    issue = make_validation_issue(requires_llm=True)
    assert issue.requires_llm is True

def test_to_json_includes_requires_llm():
    issue = make_validation_issue(requires_llm=True)
    data = issue.to_json()
    assert data["requires_llm"] is True

def test_from_json_round_trip_with_requires_llm():
    issue = make_validation_issue(requires_llm=True)
    restored = ValidationIssue.from_json(issue.to_json())
    assert restored.requires_llm is True

def test_to_markdown_llm_review():
    issue = make_validation_issue(requires_llm=True, severity=IssueSeverity.INFO)
    md = issue.to_markdown()
    assert "LLM-REVIEW" in md
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/models/test_validation_issue.py -v -k "requires_llm"`
Expected: FAIL — `requires_llm` attribute doesn't exist

**Step 3: Add the field to ValidationIssue**

In `wos/models/validation_issue.py`, add field after `suggestion`:

```python
requires_llm: bool = False
```

Update `to_markdown()`:

```python
def to_markdown(self) -> str:
    """Return markdown list item: - **SEVERITY** `file`: issue."""
    label = "LLM-REVIEW" if self.requires_llm else self.severity.value.upper()
    parts = [f"- **{label}** `{self.file}`: {self.issue}"]
    if self.suggestion:
        parts.append(f"  - {self.suggestion}")
    return "\n".join(parts)
```

**Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add wos/models/validation_issue.py tests/models/test_validation_issue.py
git commit -m "feat: add requires_llm field to ValidationIssue"
```

---

### Task 2: Inline `validate_content()` on BaseDocument — return ValidationIssue ✅

Currently `BaseDocument.validate_content()` returns `list` (of TriggerContext dicts). Change it to return `list[ValidationIssue]` with `requires_llm=True`.

**Files:**
- Modify: `wos/models/base_document.py:255-265`
- Modify: `tests/models/test_base_document.py`

**Step 1: Write the failing test**

Add to `tests/models/test_base_document.py`:

```python
def test_validate_content_returns_validation_issues(self):
    """validate_content() returns ValidationIssue objects, not raw dicts."""
    short_desc_md = (
        "---\n"
        "document_type: topic\n"
        'description: "Short"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Short Topic\n"
        "\n"
        "## Guidance\n\nContent.\n"
        "\n"
        "## Context\n\nContent.\n"
        "\n"
        "## In Practice\n\n- Do this.\n"
        "\n"
        "## Pitfalls\n\nAvoid that.\n"
        "\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )
    doc = parse_document("context/testing/example.md", short_desc_md)
    issues = doc.validate_content()
    assert len(issues) > 0
    for issue in issues:
        assert isinstance(issue, ValidationIssue)
        assert issue.requires_llm is True
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/models/test_base_document.py::TestBaseDocumentProtocol::test_validate_content_returns_validation_issues -v`
Expected: FAIL — returns TriggerContext dicts, not ValidationIssue objects

**Step 3: Rewrite `validate_content()` on BaseDocument**

In `wos/models/base_document.py`, replace the current `validate_content()` (lines 255-265):

```python
def validate_content(self) -> list[ValidationIssue]:
    """Run content quality checks that require LLM review.

    Returns ValidationIssue objects with requires_llm=True.
    Subclasses override to add type-specific content checks.
    """
    from wos.models.enums import IssueSeverity

    issues: list[ValidationIssue] = []

    # Shared: check description quality
    desc = self.frontmatter.description
    if len(desc) < 20:
        issues.append(
            ValidationIssue(
                file=self.path,
                issue="Description may be too short for agents to assess relevance",
                severity=IssueSeverity.INFO,
                validator="validate_content",
                suggestion="Expand the description to be more informative",
                requires_llm=True,
            )
        )

    return issues
```

Remove the `from wos.tier2_triggers import trigger_description_quality` import.

**Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS. Check `tests/test_tier2_triggers.py` — those tests call the trigger functions directly, not via `validate_content()`, so they should still pass.

**Step 5: Commit**

```bash
git add wos/models/base_document.py tests/models/test_base_document.py
git commit -m "feat: BaseDocument.validate_content() returns ValidationIssue with requires_llm"
```

---

### Task 3: Inline `validate_content()` on TopicDocument ✅

Move the trigger logic from `tier2_triggers.py` into `TopicDocument.validate_content()`.

**Files:**
- Modify: `wos/models/topic_document.py:49-61`
- Create: `tests/models/test_topic_document.py`

**Step 1: Write the failing test**

Create `tests/models/test_topic_document.py`:

```python
"""Tests for TopicDocument validate_content()."""
from __future__ import annotations

from wos.models.parsing import parse_document
from wos.models.validation_issue import ValidationIssue


def _make_topic(
    in_practice="- Do this step.\n- Then this.\n",
    pitfalls="Watch out for these common mistakes that developers make when working with this pattern.\n",
    go_deeper="- [Link](https://example.com)\n",
):
    md = (
        "---\n"
        "document_type: topic\n"
        'description: "A test topic with enough words to pass quality"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Test Topic\n"
        "\n"
        "## Guidance\n\nFollow these steps.\n"
        "\n"
        "## Context\n\nBackground info.\n"
        "\n"
        f"## In Practice\n\n{in_practice}"
        "\n"
        f"## Pitfalls\n\n{pitfalls}"
        "\n"
        f"## Go Deeper\n\n{go_deeper}"
    )
    return parse_document("context/testing/example.md", md)


class TestTopicValidateContent:
    def test_good_topic_no_content_issues(self):
        doc = _make_topic()
        issues = doc.validate_content()
        section_issues = [i for i in issues if i.section in ("In Practice", "Pitfalls")]
        assert len(section_issues) == 0

    def test_in_practice_no_code_or_list_flags_review(self):
        doc = _make_topic(in_practice="Just some prose without examples.\n")
        issues = doc.validate_content()
        in_practice = [i for i in issues if i.section == "In Practice"]
        assert len(in_practice) > 0
        assert all(i.requires_llm for i in in_practice)

    def test_pitfalls_too_short_flags_review(self):
        doc = _make_topic(pitfalls="Be careful.\n")
        issues = doc.validate_content()
        pitfall = [i for i in issues if i.section == "Pitfalls"]
        assert len(pitfall) > 0
        assert all(i.requires_llm for i in pitfall)

    def test_all_content_issues_are_validation_issues(self):
        doc = _make_topic(in_practice="Prose only.\n", pitfalls="Short.\n")
        issues = doc.validate_content()
        for issue in issues:
            assert isinstance(issue, ValidationIssue)
            assert issue.requires_llm is True
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/models/test_topic_document.py -v`
Expected: FAIL — current `validate_content()` returns TriggerContext dicts

**Step 3: Rewrite `validate_content()` on TopicDocument**

In `wos/models/topic_document.py`, replace the `validate_content()` method:

```python
def validate_content(self) -> list[ValidationIssue]:
    from wos.models.enums import IssueSeverity

    issues = super().validate_content()

    # Check In Practice concreteness
    section = self.get_section_content("In Practice", "")
    if section:
        has_code = "```" in section or "    " in section
        has_list = "- " in section or "1. " in section
        if not has_code and not has_list:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="In Practice section may lack concrete examples",
                    severity=IssueSeverity.INFO,
                    validator="validate_content",
                    section="In Practice",
                    suggestion="Add code blocks, bullet lists, or step-by-step examples",
                    requires_llm=True,
                )
            )

    # Check Pitfalls completeness
    pitfalls = self.get_section_content("Pitfalls", "")
    if pitfalls and len(pitfalls.split()) < 20:
        issues.append(
            ValidationIssue(
                file=self.path,
                issue="Pitfalls section may be incomplete",
                severity=IssueSeverity.INFO,
                validator="validate_content",
                section="Pitfalls",
                suggestion="Add more common pitfalls and how to avoid them",
                requires_llm=True,
            )
        )

    return issues
```

**Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add wos/models/topic_document.py tests/models/test_topic_document.py
git commit -m "feat: inline validate_content() on TopicDocument"
```

---

### Task 4: Inline `validate_content()` on OverviewDocument, ResearchDocument, PlanDocument ✅

Same pattern as Task 3 for the remaining subclasses.

**Files:**
- Modify: `wos/models/overview_document.py:45-50`
- Modify: `wos/models/research_document.py:48-60`
- Modify: `wos/models/plan_document.py:37-49`
- Create: `tests/models/test_overview_document.py`
- Create: `tests/models/test_research_document.py`
- Create: `tests/models/test_plan_document.py`

**Step 1: Write the failing tests**

Create `tests/models/test_overview_document.py`:

```python
"""Tests for OverviewDocument validate_content()."""
from __future__ import annotations

from wos.models.parsing import parse_document
from wos.models.validation_issue import ValidationIssue


def _make_overview(what_this_covers="This area covers a wide range of topics " * 5):
    md = (
        "---\n"
        "document_type: overview\n"
        'description: "Test overview with enough words"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Test Overview\n"
        "\n"
        f"## What This Covers\n\n{what_this_covers}\n"
        "\n"
        "## Topics\n\n- Topic A\n"
        "\n"
        "## Key Sources\n\n- [Source](https://example.com)\n"
    )
    return parse_document("context/testing/_overview.md", md)


class TestOverviewValidateContent:
    def test_short_coverage_flags_review(self):
        doc = _make_overview(what_this_covers="Brief.")
        issues = doc.validate_content()
        coverage = [i for i in issues if i.section == "What This Covers"]
        assert len(coverage) > 0
        assert all(isinstance(i, ValidationIssue) for i in coverage)
        assert all(i.requires_llm for i in coverage)

    def test_adequate_coverage_no_issue(self):
        doc = _make_overview()
        issues = doc.validate_content()
        coverage = [i for i in issues if i.section == "What This Covers"]
        assert len(coverage) == 0
```

Create `tests/models/test_research_document.py`:

```python
"""Tests for ResearchDocument validate_content()."""
from __future__ import annotations

from wos.models.parsing import parse_document
from wos.models.validation_issue import ValidationIssue


def _make_research(
    question="What is the best approach?",
    findings="Based on [Source](https://example.com), the approach works well.\n",
):
    md = (
        "---\n"
        "document_type: research\n"
        'description: "Test research document"\n'
        "last_updated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Test Research\n"
        "\n"
        f"## Question\n\n{question}\n"
        "\n"
        f"## Findings\n\n{findings}"
        "\n"
        "## Implications\n\nThis means we should do X.\n"
    )
    return parse_document("artifacts/research/2026-02-17-test.md", md)


class TestResearchValidateContent:
    def test_question_no_question_mark_flags_review(self):
        doc = _make_research(question="Investigate the pattern")
        issues = doc.validate_content()
        q_issues = [i for i in issues if i.section == "Question"]
        assert len(q_issues) > 0
        assert all(i.requires_llm for i in q_issues)

    def test_findings_no_links_flags_review(self):
        long_text = "The results show that this approach works. " * 10
        doc = _make_research(findings=long_text)
        issues = doc.validate_content()
        f_issues = [i for i in issues if i.section == "Findings"]
        assert len(f_issues) > 0
        assert all(i.requires_llm for i in f_issues)

    def test_good_research_no_content_issues(self):
        doc = _make_research()
        issues = doc.validate_content()
        section_issues = [i for i in issues if i.section in ("Question", "Findings")]
        assert len(section_issues) == 0
```

Create `tests/models/test_plan_document.py`:

```python
"""Tests for PlanDocument validate_content()."""
from __future__ import annotations

from wos.models.parsing import parse_document
from wos.models.validation_issue import ValidationIssue


def _make_plan(
    steps="1. Do first thing in detail with clear instructions.\n2. Do second thing with all needed context.\n",
    verification="- Check output matches expected.\n- Verify no regressions.\n",
):
    md = (
        "---\n"
        "document_type: plan\n"
        'description: "Test plan document"\n'
        "last_updated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Test Plan\n"
        "\n"
        "## Objective\n\nAccomplish the goal.\n"
        "\n"
        "## Context\n\nBackground info here.\n"
        "\n"
        f"## Steps\n\n{steps}"
        "\n"
        f"## Verification\n\n{verification}"
    )
    return parse_document("artifacts/plans/2026-02-17-test.md", md)


class TestPlanValidateContent:
    def test_vague_steps_flags_review(self):
        doc = _make_plan(steps="1. Do it.\n2. Test.\n3. Ship.\n")
        issues = doc.validate_content()
        step_issues = [i for i in issues if i.section == "Steps"]
        assert len(step_issues) > 0
        assert all(i.requires_llm for i in step_issues)

    def test_sparse_verification_flags_review(self):
        doc = _make_plan(verification="- Works.\n")
        issues = doc.validate_content()
        v_issues = [i for i in issues if i.section == "Verification"]
        assert len(v_issues) > 0
        assert all(i.requires_llm for i in v_issues)

    def test_good_plan_no_content_issues(self):
        doc = _make_plan()
        issues = doc.validate_content()
        section_issues = [i for i in issues if i.section in ("Steps", "Verification")]
        assert len(section_issues) == 0
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/models/test_overview_document.py tests/models/test_research_document.py tests/models/test_plan_document.py -v`
Expected: FAIL

**Step 3: Rewrite `validate_content()` on each subclass**

**OverviewDocument** (`wos/models/overview_document.py`) — replace `validate_content()`:

```python
def validate_content(self) -> list[ValidationIssue]:
    from wos.models.enums import IssueSeverity

    issues = super().validate_content()

    section = self.get_section_content("What This Covers", "")
    if section and len(section.split()) < 50:
        issues.append(
            ValidationIssue(
                file=self.path,
                issue="What This Covers section may be too vague to define scope",
                severity=IssueSeverity.INFO,
                validator="validate_content",
                section="What This Covers",
                suggestion="Expand to clearly define scope and audience",
                requires_llm=True,
            )
        )

    return issues
```

**ResearchDocument** (`wos/models/research_document.py`) — replace `validate_content()`:

```python
def validate_content(self) -> list[ValidationIssue]:
    from wos.models.enums import IssueSeverity

    issues = super().validate_content()

    # Check question clarity
    question = self.get_section_content("Question", "")
    if question and "?" not in question:
        issues.append(
            ValidationIssue(
                file=self.path,
                issue="Research question may not be clearly framed as a question",
                severity=IssueSeverity.INFO,
                validator="validate_content",
                section="Question",
                suggestion="Frame as a specific, answerable question",
                requires_llm=True,
            )
        )

    # Check finding groundedness
    findings = self.get_section_content("Findings", "")
    has_links = "[" in findings and "](" in findings
    if findings and not has_links and len(findings.split()) > 50:
        issues.append(
            ValidationIssue(
                file=self.path,
                issue="Findings may not be well-grounded in sources",
                severity=IssueSeverity.INFO,
                validator="validate_content",
                section="Findings",
                suggestion="Add citations or links to supporting sources",
                requires_llm=True,
            )
        )

    return issues
```

**PlanDocument** (`wos/models/plan_document.py`) — replace `validate_content()`:

```python
def validate_content(self) -> list[ValidationIssue]:
    from wos.models.enums import IssueSeverity

    issues = super().validate_content()

    # Check step specificity
    steps = self.get_section_content("Steps", "")
    if steps:
        step_lines = [
            line for line in steps.split("\n")
            if line.strip() and line.strip()[0].isdigit()
        ]
        if len(step_lines) > 0 and len(steps.split()) / len(step_lines) < 10:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="Plan steps may be too vague to execute",
                    severity=IssueSeverity.INFO,
                    validator="validate_content",
                    section="Steps",
                    suggestion="Add detail so steps are unambiguous",
                    requires_llm=True,
                )
            )

    # Check verification completeness
    verification = self.get_section_content("Verification", "")
    if verification:
        items = [
            line for line in verification.split("\n")
            if line.strip().startswith("-")
        ]
        if len(items) < 2:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="Verification section may not have enough criteria",
                    severity=IssueSeverity.INFO,
                    validator="validate_content",
                    section="Verification",
                    suggestion="Add verification criteria for each objective",
                    requires_llm=True,
                )
            )

    return issues
```

**Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add wos/models/overview_document.py wos/models/research_document.py wos/models/plan_document.py tests/models/test_overview_document.py tests/models/test_research_document.py tests/models/test_plan_document.py
git commit -m "feat: inline validate_content() on Overview, Research, Plan documents"
```

---

### Task 5: Add `auto_fix()` to BaseDocument ✅

Absorb `auto_fix.py` logic into domain objects. `auto_fix()` returns fixed markdown string or None.

**Files:**
- Modify: `wos/models/base_document.py`
- Modify: `tests/models/test_base_document.py`

**Step 1: Write the failing test**

Add to `tests/models/test_base_document.py`:

```python
# -- auto_fix --

def test_auto_fix_reorders_sections(self):
    """auto_fix() should fix section ordering issues."""
    bad_order_md = (
        "---\n"
        "document_type: topic\n"
        'description: "Test topic document"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Test Topic\n"
        "\n"
        "## Context\n\nBackground info.\n"
        "\n"
        "## Guidance\n\nFollow these steps.\n"
        "\n"
        "## In Practice\n\n- Do this.\n"
        "\n"
        "## Pitfalls\n\nAvoid that.\n"
        "\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )
    doc = parse_document("context/testing/example.md", bad_order_md)
    fixed = doc.auto_fix()
    assert fixed is not None
    assert fixed.index("## Guidance") < fixed.index("## Context")

def test_auto_fix_returns_none_when_valid(self):
    """auto_fix() returns None for a valid document."""
    doc = self._make_topic_doc()
    fixed = doc.auto_fix()
    assert fixed is None
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/models/test_base_document.py -v -k "auto_fix"`
Expected: FAIL — `auto_fix` doesn't exist

**Step 3: Add `auto_fix()` to BaseDocument**

In `wos/models/base_document.py`, add after `validate_content()`. The implementation should:

1. Call `self.validate_self()` to get issues
2. For each issue, check if a fix is available by validator name
3. Apply fixes sequentially to the raw content
4. Return the fixed content, or None if no fixes applied
5. Validate the fixed content by re-parsing before returning

Key fix handlers to port from `auto_fix.py`:
- `check_section_ordering` → `_fix_section_ordering(content)` — reorder H2 sections to canonical order
- `check_section_presence` → `_fix_missing_section(content, section_name)` — add TODO placeholder

See `wos/auto_fix.py` for the complete regex-based implementation of each fix function. Port the logic into private methods `_fix_section_ordering()` and `_fix_missing_section()` on BaseDocument.

**Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add wos/models/base_document.py tests/models/test_base_document.py
git commit -m "feat: add auto_fix() to BaseDocument"
```

---

### Task 6: Rename `ContextArea.validate()` to `validate_self()`, add `is_valid` ✅

**Files:**
- Modify: `wos/models/context_area.py:115-120`
- Modify: `tests/models/test_context_area.py`
- Modify: any callers of `area.validate()` (search codebase)

**Step 1: Write the failing test**

Add to `tests/models/test_context_area.py`:

```python
def test_validate_self_returns_list(self):
    """validate_self() replaces validate()."""
    area = ContextArea(name="testing")
    issues = area.validate_self()
    assert isinstance(issues, list)

def test_is_valid_property(self):
    area = ContextArea(name="testing")
    assert isinstance(area.is_valid, bool)
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/models/test_context_area.py -v -k "validate_self or is_valid"`
Expected: FAIL

**Step 3: Rename and add `is_valid`**

In `wos/models/context_area.py`, rename `validate()` to `validate_self()`:

```python
def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
    """Run area-level validators (overview-topic sync, naming)."""
    issues: list[ValidationIssue] = []
    issues.extend(self._check_overview_topic_sync())
    issues.extend(self._check_naming_conventions())
    return issues

@property
def is_valid(self) -> bool:
    return len(self.validate_self()) == 0
```

Search for callers of `.validate()` on ContextArea and update them. Check:
- `scripts/check_health.py`
- `tests/models/test_context_area.py`

**Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add wos/models/context_area.py tests/models/test_context_area.py
git commit -m "feat: rename ContextArea.validate() to validate_self(), add is_valid"
```

---

### Task 7: Add `from_documents()` factory and collection protocol to ContextArea ✅

**Files:**
- Modify: `wos/models/context_area.py`
- Modify: `tests/models/test_context_area.py`

**Step 1: Write the failing tests**

```python
def test_from_documents_groups_by_area(self):
    from wos.models.parsing import parse_document

    topic_md = (
        "---\n"
        "document_type: topic\n"
        'description: "Test topic"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n\n# Topic\n\n## Guidance\n\nContent.\n\n## Context\n\nContent.\n"
        "\n## In Practice\n\n- Do.\n\n## Pitfalls\n\nAvoid.\n"
        "\n## Go Deeper\n\n- [L](https://e.com)\n"
    )
    overview_md = (
        "---\n"
        "document_type: overview\n"
        'description: "Test overview"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n\n# Testing\n\n## What This Covers\n\nScope.\n"
        "\n## Topics\n\n- Topic\n\n## Key Sources\n\n- [S](https://e.com)\n"
    )
    docs = [
        parse_document("context/testing/topic.md", topic_md),
        parse_document("context/testing/_overview.md", overview_md),
    ]
    areas = ContextArea.from_documents(docs)
    assert len(areas) == 1
    assert areas[0].name == "testing"
    assert areas[0].overview is not None
    assert len(areas[0].topics) == 1

def test_str(self):
    area = ContextArea(name="testing")
    assert "Testing" in str(area)

def test_repr(self):
    area = ContextArea(name="testing")
    assert "ContextArea" in repr(area)

def test_len(self):
    area = ContextArea(name="testing")
    assert len(area) == 0

def test_iter(self):
    area = ContextArea(name="testing")
    assert list(area) == []

def test_contains(self):
    area = ContextArea(name="testing")
    assert "nonexistent" not in area
```

**Step 2: Run tests to verify they fail**

**Step 3: Add `from_documents()` and collection protocol**

In `wos/models/context_area.py`:

```python
@classmethod
def from_documents(cls, docs: list) -> List[ContextArea]:
    """Group parsed documents into ContextArea objects by area directory."""
    area_map: dict[str, ContextArea] = {}
    for doc in docs:
        if doc.document_type not in {DocumentType.TOPIC, DocumentType.OVERVIEW}:
            continue
        area_name = doc.area_name
        if not area_name:
            continue
        if area_name not in area_map:
            area_map[area_name] = cls(name=area_name)
        area = area_map[area_name]
        if doc.document_type == DocumentType.OVERVIEW:
            area.overview = doc
        elif doc.document_type == DocumentType.TOPIC:
            area.topics.append(doc)
    return sorted(area_map.values(), key=lambda a: a.name)

def __str__(self) -> str:
    return f"{self.display_name} ({len(self.topics)} topics)"

def __repr__(self) -> str:
    return f"ContextArea(name={self.name!r}, topics={len(self.topics)})"

def __len__(self) -> int:
    return len(self.topics)

def __iter__(self):
    return iter(self.topics)

def __contains__(self, item: object) -> bool:
    if isinstance(item, str):
        return any(t.title == item for t in self.topics)
    return item in self.topics
```

**Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add wos/models/context_area.py tests/models/test_context_area.py
git commit -m "feat: add from_documents(), collection protocol to ContextArea"
```

---

## Phase B: New Domain Objects ✅ COMPLETE

### Task 8: Create RulesFile value object ✅

**Files:**
- Create: `wos/models/rules_file.py`
- Create: `tests/models/test_rules_file.py`
- Modify: `tests/builders.py` — add `make_rules_file()`

**Step 1: Write the failing test**

Create `tests/models/test_rules_file.py`:

```python
"""Tests for RulesFile value object."""
from __future__ import annotations

from wos.models.rules_file import RulesFile
from wos.models.validation_issue import ValidationIssue


class TestRulesFile:
    def test_render_produces_content(self):
        rf = RulesFile.render()
        assert isinstance(rf, RulesFile)
        assert "Document Types" in rf.content

    def test_to_markdown(self):
        rf = RulesFile.render()
        assert isinstance(rf.to_markdown(), str)
        assert rf.to_markdown() == rf.content

    def test_validate_self_valid(self):
        rf = RulesFile.render()
        assert rf.validate_self() == []

    def test_is_valid(self):
        rf = RulesFile.render()
        assert rf.is_valid is True

    def test_str(self):
        rf = RulesFile.render()
        assert "lines" in str(rf).lower() or "RulesFile" in str(rf)

    def test_empty_content_not_valid(self):
        rf = RulesFile(content="")
        assert rf.is_valid is False

    def test_frozen(self):
        import pytest
        rf = RulesFile.render()
        with pytest.raises(Exception):
            rf.content = "changed"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/models/test_rules_file.py -v`
Expected: FAIL — module doesn't exist

**Step 3: Create `wos/models/rules_file.py`**

```python
"""RulesFile — value object for .claude/rules/wos-context.md."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict

from wos.models.enums import IssueSeverity
from wos.models.validation_issue import ValidationIssue


class RulesFile(BaseModel):
    """The behavioral guide for agents (.claude/rules/wos-context.md)."""

    model_config = ConfigDict(frozen=True)

    content: str

    def __str__(self) -> str:
        lines = self.content.count("\n")
        return f"RulesFile ({lines} lines)"

    def __repr__(self) -> str:
        return f"RulesFile(content_length={len(self.content)})"

    def to_markdown(self) -> str:
        return self.content

    def to_json(self) -> dict:
        return {"content": self.content}

    @classmethod
    def from_json(cls, data: dict) -> RulesFile:
        return cls(**data)

    def validate_self(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not self.content.strip():
            issues.append(
                ValidationIssue(
                    file=".claude/rules/wos-context.md",
                    issue="Rules file is empty",
                    severity=IssueSeverity.WARN,
                    validator="RulesFile.validate_self",
                    suggestion="Generate rules file via discovery",
                )
            )
        return issues

    @property
    def is_valid(self) -> bool:
        return len(self.validate_self()) == 0

    @classmethod
    def render(cls) -> RulesFile:
        """Generate the standard rules file content."""
        # Port content from discovery.render_rules_file()
        content = """\
# WOS Context Rules

## Document Types

| Type | Directory | Purpose |
|------|-----------|---------|
| topic | `context/{area}/{slug}.md` | Actionable guidance with citations |
| overview | `context/{area}/_overview.md` | Area orientation and topic index |
| research | `artifacts/research/{date}-{slug}.md` | Investigation snapshot |
| plan | `artifacts/plans/{date}-{slug}.md` | Actionable work plan |

## Frontmatter Requirements

All documents require YAML frontmatter with `document_type`, `description`,
and `last_updated`. Additional requirements by type:

- **topic**: `sources` (list of url+title), `last_validated` (date)
- **overview**: `last_validated` (date)
- **research**: `sources` (list of url+title)
- **plan**: (optional `status` string)

Optional on all types: `tags` (lowercase-hyphenated), `related` (file paths or URLs).

## Agent Guidelines

- Use `/wos:discover` to find and access context before reading full files
- Context types (topic, overview) appear in the AGENTS.md manifest
- Artifact types (research, plan) are internal \u2014 reachable via `related` links
- Use `/wos:create-document` to create new documents
- Use `/wos:update-document` to update existing documents
- Use `/wos:audit` to check document validity
- Use `/wos:fix` to fix issues found by audit
- `related` uses root-relative file paths (e.g., `context/python/error-handling.md`)
- Never edit content between wos markers manually \u2014 auto-generated by discovery
"""
        return cls(content=content)
```

**Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add wos/models/rules_file.py tests/models/test_rules_file.py
git commit -m "feat: add RulesFile value object"
```

---

### Task 9: Create AgentsMd entity ✅

**Files:**
- Create: `wos/models/agents_md.py`
- Create: `tests/models/test_agents_md.py`
- Modify: `tests/builders.py` — add `make_agents_md()`

This entity owns the AGENTS.md file. Port logic from `discovery.py`: `_replace_between_markers()`, `render_manifest()`, `_agents_md_template()`.

Key methods:
- `from_content(cls, path, content)` — parse existing file
- `from_template(cls, path)` — create new from template
- `update_manifest(areas: list[ContextArea])` — re-render manifest between markers, return new AgentsMd
- `to_markdown()` — full content
- `validate_self()` — check markers exist, content not empty
- `is_valid`, `__str__`, `__repr__`

Follow same TDD pattern: write tests first, verify fail, implement, verify pass, commit.

Commit: `git commit -m "feat: add AgentsMd entity"`

---

### Task 10: Create ClaudeMd entity ✅

**Files:**
- Create: `wos/models/claude_md.py`
- Create: `tests/models/test_claude_md.py`
- Modify: `tests/builders.py` — add `make_claude_md()`

Port logic from `discovery.py`: `update_claude_md()`, `_strip_marker_section()`, `_claude_md_template()`.

Key methods:
- `from_content(cls, path, content)` — parse existing file
- `ensure_agents_ref()` — add @AGENTS.md reference if missing, return new ClaudeMd
- `strip_old_markers()` — remove old WOS context markers
- `to_markdown()`, `validate_self()`, `is_valid`, `__str__`, `__repr__`

Commit: `git commit -m "feat: add ClaudeMd entity"`

---

### Task 11: Create CommunicationPreferences value object ✅

**Files:**
- Create: `wos/models/communication_preferences.py`
- Create: `tests/models/test_communication_preferences.py`
- Modify: `tests/builders.py` — add `make_communication_preferences()`

Port from `preferences.py`: `DIMENSIONS`, `DIMENSION_INSTRUCTIONS`, `render_preferences()`.

Key:
- `dimensions: dict[str, str]` — e.g. `{"directness": "blunt", "tone": "casual"}`
- `render_section()` — render as markdown instructions
- `validate_self()` — check all dimension keys/values are valid
- `is_valid`, `__str__`, `__repr__`
- Frozen value object

Commit: `git commit -m "feat: add CommunicationPreferences value object"`

---

## Phase C: ProjectContext Aggregate

### Task 12: Create ProjectContext aggregate root ✅

**Files:**
- Create: `wos/models/project_context.py`
- Create: `tests/models/test_project_context.py`
- Modify: `tests/builders.py` — add `make_project_context()`

Start with construction and basic protocol:

```python
class ProjectContext(BaseModel):
    root: str
    areas: List[ContextArea] = []
    agents_md: Optional[AgentsMd] = None
    claude_md: Optional[ClaudeMd] = None
    rules_file: Optional[RulesFile] = None
```

Methods:
- `from_directory(cls, root: str)` — scan areas, read files
- `__len__`, `__iter__`, `__contains__` — over areas
- `__str__`, `__repr__`
- `validate_self(deep=False)` — delegates to each area's `validate_self()` + cross-area checks
- `is_valid`

Commit: `git commit -m "feat: add ProjectContext aggregate root"`

---

### Task 13: Add `scaffold()` and `add_area()` to ProjectContext

Absorb `scaffold.py` logic into ProjectContext methods.

**Files:**
- Modify: `wos/models/project_context.py`
- Modify: `tests/models/test_project_context.py`

Commit: `git commit -m "feat: add scaffold() and add_area() to ProjectContext"`

---

### Task 14: Add `discover()` to ProjectContext

Absorb `discovery.run_discovery()` logic.

**Files:**
- Modify: `wos/models/project_context.py`
- Modify: `tests/models/test_project_context.py`

Commit: `git commit -m "feat: add discover() to ProjectContext"`

---

## Phase D: Thin Out Modules

### Task 15: Thin `discovery.py` to CLI adapter

Replace functions with delegations to `ProjectContext` and its owned objects.

**Files:**
- Modify: `wos/discovery.py`
- Verify: `tests/test_discovery.py` still passes

Commit: `git commit -m "refactor: thin discovery.py to ProjectContext adapter"`

---

### Task 16: Thin `scaffold.py` to CLI adapter

**Files:**
- Modify: `wos/scaffold.py`
- Verify: `tests/test_scaffold.py` still passes

Commit: `git commit -m "refactor: thin scaffold.py to ProjectContext adapter"`

---

### Task 17: Update `cross_validators.py` to use domain methods

Replace `_build_context_areas()` with `ContextArea.from_documents()`.
Replace `_extract_area()` calls with `doc.area_name`.

**Files:**
- Modify: `wos/cross_validators.py`
- Verify: `tests/test_cross_validators.py` still passes

Commit: `git commit -m "refactor: cross_validators uses domain methods"`

---

### Task 18: Delete absorbed modules ✅

Delete `wos/tier2_triggers.py` (logic inlined into `validate_content()`).
Update remaining imports. Delete or update `tests/test_tier2_triggers.py`.

Note: `wos/auto_fix.py` stays for now — it's still used by `scripts/run_auto_fix.py` and the `/wos:fix` skill. It can be thinned to delegate to `doc.auto_fix()` but doesn't need to be deleted yet.

**Files:**
- Delete: `wos/tier2_triggers.py`
- Modify or delete: `tests/test_tier2_triggers.py`
- Modify: any remaining imports of `tier2_triggers`

Commit: `git commit -m "refactor: delete tier2_triggers.py (absorbed into domain objects)"`

---

### Task 19: Final cleanup and CLAUDE.md update ✅

- Update `wos/models/__init__.py` to export new types
- Add missing builders to `tests/builders.py`
- Verify all tests pass
- Update CLAUDE.md architecture section to reflect new structure

Commit: `git commit -m "chore: final cleanup and CLAUDE.md update"`

---

## Verification Checklist

After all tasks:

1. `python3 -m pytest tests/ -v` — all tests pass
2. Every domain object has: `validate_self()`, `is_valid`, `__str__`, `__repr__`
3. `validate_content()` returns `ValidationIssue` with `requires_llm=True` on all document subclasses
4. `auto_fix()` on BaseDocument handles section ordering and missing sections
5. New domain objects created: RulesFile, AgentsMd, ClaudeMd, CommunicationPreferences, ProjectContext
6. `ContextArea` has `validate_self()`, `is_valid`, `from_documents()`, collection protocol
7. `tier2_triggers.py` deleted
8. `tests/builders.py` has `make_*()` for every domain object
9. CLAUDE.md documents the updated architecture
