# DDD Domain Model Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich every domain object in `wos/models/` with a standard DDD protocol (constructors, equality, representations, self-validation, collection interfaces, token estimation, test builders) and absorb helper modules into the domain objects they serve.

**Architecture:** Bottom-up enrichment. Start with leaf value objects (CitedSource, ValidationIssue, DocumentSection), then work up to documents and aggregates. Each phase builds on the previous. Value objects get `frozen=True`. Documents absorb validators and templates. Aggregates absorb formatting and orchestration.

**Tech Stack:** Python 3.9, Pydantic v2, pytest. `from __future__ import annotations` everywhere. `Optional[X]` for runtime expressions.

**Design doc:** `docs/plans/2026-02-20-ddd-domain-model-enrichment-design.md`

---

## Phase 1: Value Objects

### Task 1: Create tests/builders.py module and enrich CitedSource

**Files:**
- Create: `tests/builders.py`
- Modify: `wos/models/core.py:76-108`
- Test: `tests/test_ddd_protocol.py` (new)

**Step 1: Create test file with CitedSource protocol tests**

Create `tests/test_ddd_protocol.py`:

```python
"""Tests for DDD protocol on domain objects.

Each domain object is tested for: construction, equality, str/repr,
to_json/from_json round-trip, to_markdown (where applicable),
validate_self, is_valid, and test builder.
"""

from __future__ import annotations

from wos.models.core import CitedSource, IssueSeverity


# ── CitedSource ──────────────────────────────────────────────


class TestCitedSourceProtocol:
    def test_frozen_immutable(self):
        s = CitedSource(url="https://example.com", title="Example")
        import pytest
        with pytest.raises(Exception):
            s.url = "https://other.com"

    def test_frozen_hashable(self):
        s = CitedSource(url="https://example.com", title="Example")
        assert hash(s) == hash(CitedSource(url="https://example.com", title="Example"))
        assert s in {s}

    def test_equality(self):
        a = CitedSource(url="https://a.com", title="A")
        b = CitedSource(url="https://a.com", title="A")
        c = CitedSource(url="https://b.com", title="B")
        assert a == b
        assert a != c

    def test_str(self):
        s = CitedSource(url="https://example.com/article", title="Example Article")
        assert str(s) == "[Example Article](https://example.com/article)"

    def test_repr(self):
        s = CitedSource(url="https://example.com", title="Example")
        r = repr(s)
        assert "CitedSource" in r
        assert "example.com" in r

    def test_to_json(self):
        s = CitedSource(url="https://example.com", title="Example")
        d = s.to_json()
        assert d == {"url": "https://example.com", "title": "Example"}

    def test_from_json(self):
        d = {"url": "https://example.com", "title": "Example"}
        s = CitedSource.from_json(d)
        assert s.url == "https://example.com"
        assert s.title == "Example"

    def test_json_round_trip(self):
        original = CitedSource(url="https://example.com", title="Example")
        restored = CitedSource.from_json(original.to_json())
        assert restored == original

    def test_to_markdown(self):
        s = CitedSource(url="https://example.com", title="Example")
        assert s.to_markdown() == "[Example](https://example.com)"

    def test_from_markdown_link(self):
        s = CitedSource.from_markdown_link("[Example](https://example.com)")
        assert s.url == "https://example.com"
        assert s.title == "Example"

    def test_markdown_round_trip(self):
        original = CitedSource(url="https://example.com", title="Example")
        restored = CitedSource.from_markdown_link(original.to_markdown())
        assert restored == original

    def test_from_markdown_link_invalid(self):
        import pytest
        with pytest.raises(ValueError, match="markdown link"):
            CitedSource.from_markdown_link("not a link")

    def test_to_yaml_entry(self):
        s = CitedSource(url="https://example.com", title="Example")
        yaml = s.to_yaml_entry()
        assert '  - url: "https://example.com"' in yaml
        assert '    title: "Example"' in yaml

    def test_validate_self_valid(self):
        s = CitedSource(url="https://example.com", title="Example")
        assert s.validate_self() == []

    def test_validate_self_bad_scheme(self):
        s = CitedSource(url="ftp://example.com", title="Example")
        issues = s.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.FAIL
        assert "scheme" in issues[0].issue.lower()

    def test_validate_self_empty_title(self):
        s = CitedSource(url="https://example.com", title="   ")
        issues = s.validate_self()
        assert any("title" in i.issue.lower() for i in issues)

    def test_is_valid_true(self):
        s = CitedSource(url="https://example.com", title="Example")
        assert s.is_valid is True

    def test_is_valid_false(self):
        s = CitedSource(url="not-a-url", title="Example")
        assert s.is_valid is False
```

**Step 2: Create test builder module**

Create `tests/builders.py`:

```python
"""Test builders for WOS domain objects.

Each make_*() function returns a valid domain object with sensible defaults.
Override any field via keyword arguments.
"""

from __future__ import annotations

from wos.models.core import CitedSource


def make_cited_source(**overrides) -> CitedSource:
    """Build a valid CitedSource with sensible defaults."""
    defaults = {
        "url": "https://example.com/article",
        "title": "Example Article",
    }
    defaults.update(overrides)
    return CitedSource(**defaults)
```

**Step 3: Add builder test**

Append to `tests/test_ddd_protocol.py`:

```python
class TestCitedSourceBuilder:
    def test_builder_returns_valid(self):
        from tests.builders import make_cited_source
        s = make_cited_source()
        assert s.is_valid

    def test_builder_override(self):
        from tests.builders import make_cited_source
        s = make_cited_source(url="https://custom.com")
        assert s.url == "https://custom.com"
        assert s.title == "Example Article"  # default preserved
```

**Step 4: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ddd_protocol.py -v`
Expected: FAIL — `CitedSource` has no `frozen`, `__str__`, `to_json`, etc.

**Step 5: Implement CitedSource DDD protocol**

Modify `wos/models/core.py:76-108` — replace the `CitedSource` class:

```python
class CitedSource(BaseModel):
    """A cited source with URL and title."""

    model_config = ConfigDict(frozen=True)

    url: str
    title: str

    # ── Representations ─────────────────────────────────────

    def __str__(self) -> str:
        return f"[{self.title}]({self.url})"

    def __repr__(self) -> str:
        return f"CitedSource(url={self.url!r}, title={self.title!r})"

    def to_json(self) -> dict:
        """JSON-serializable dict."""
        return self.model_dump(mode="json")

    def to_markdown(self) -> str:
        """Markdown link format: [title](url)"""
        return f"[{self.title}]({self.url})"

    def to_yaml_entry(self) -> str:
        """YAML list entry for frontmatter sources block."""
        escaped_url = self.url.replace("\\", "\\\\").replace('"', '\\"')
        escaped_title = self.title.replace("\\", "\\\\").replace('"', '\\"')
        return f'  - url: "{escaped_url}"\n    title: "{escaped_title}"'

    # ── Construction ────────────────────────────────────────

    @classmethod
    def from_json(cls, data: dict) -> CitedSource:
        """Construct from a JSON-compatible dict."""
        return cls.model_validate(data)

    @classmethod
    def from_markdown_link(cls, md_link: str) -> CitedSource:
        """Parse from markdown link format: [title](url)"""
        match = re.match(r"\[(.+?)\]\((.+?)\)", md_link)
        if not match:
            raise ValueError(f"Not a valid markdown link: {md_link}")
        return cls(url=match.group(2), title=match.group(1))

    # ── Validation ──────────────────────────────────────────

    def validate_self(self, deep: bool = False) -> list:
        """Check internal validity. deep=True adds URL reachability."""
        from wos.models.core import ValidationIssue, IssueSeverity

        issues: list[ValidationIssue] = []
        if not self.url.startswith(("http://", "https://")):
            issues.append(ValidationIssue(
                file="",
                issue=f"URL '{self.url}' missing http(s) scheme",
                severity=IssueSeverity.FAIL,
                validator="cited_source_url_scheme",
            ))
        if not self.title.strip():
            issues.append(ValidationIssue(
                file="",
                issue="Source title is blank",
                severity=IssueSeverity.FAIL,
                validator="cited_source_title",
            ))
        if deep and not issues:
            result = self.check_reachability()
            if not result.reachable:
                issues.append(ValidationIssue(
                    file="",
                    issue=f"URL unreachable: {self.url} — {result.reason}",
                    severity=IssueSeverity.WARN,
                    validator="cited_source_reachability",
                ))
        return issues

    @property
    def is_valid(self) -> bool:
        """True if validate_self() returns no issues."""
        return len(self.validate_self()) == 0

    # ── Existing methods (unchanged) ────────────────────────

    def normalize_title(self) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        text = self.title.lower()
        text = text.replace("\u2013", " ").replace("\u2014", " ")
        text = re.sub(r"[^a-z0-9 ]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def get_estimated_tokens(self) -> int:
        """Estimate token cost of this source citation."""
        return len(self.url) // 3 + len(self.title) // 4 + 5

    def check_reachability(self):
        """HTTP HEAD check. Returns ReachabilityResult."""
        from wos.source_verification import check_url_reachability

        return check_url_reachability(self.url)

    def verify(self):
        """Full verification — reachability + title match. Returns VerificationResult."""
        from wos.source_verification import verify_source

        return verify_source(self.url, self.title)
```

Also add the import at top of `wos/models/core.py`:

```python
from pydantic import BaseModel, ConfigDict
```

**Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_ddd_protocol.py -v`
Expected: ALL PASS

**Step 7: Run full test suite to check for regressions**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS (frozen=True may cause regressions if any test mutates CitedSource — fix by using model_copy)

**Step 8: Commit**

```bash
git add wos/models/core.py tests/test_ddd_protocol.py tests/builders.py
git commit -m "feat: enrich CitedSource with DDD protocol (frozen, str, json, markdown, validate_self)"
```

---

### Task 2: Enrich ValidationIssue

**Files:**
- Modify: `wos/models/core.py:44-52`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)

**Step 1: Add ValidationIssue protocol tests**

Append to `tests/test_ddd_protocol.py`:

```python
from wos.models.core import ValidationIssue, IssueSeverity


class TestValidationIssueProtocol:
    def test_frozen_immutable(self):
        import pytest
        vi = ValidationIssue(
            file="test.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="test_validator",
        )
        with pytest.raises(Exception):
            vi.file = "other.md"

    def test_frozen_hashable(self):
        vi = ValidationIssue(
            file="test.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="test_validator",
        )
        assert vi in {vi}

    def test_equality(self):
        a = ValidationIssue(
            file="a.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="v",
        )
        b = ValidationIssue(
            file="a.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="v",
        )
        assert a == b

    def test_str(self):
        vi = ValidationIssue(
            file="context/test.md", issue="Missing section",
            severity=IssueSeverity.FAIL, validator="check",
        )
        s = str(vi)
        assert "FAIL" in s
        assert "context/test.md" in s
        assert "Missing section" in s

    def test_repr(self):
        vi = ValidationIssue(
            file="test.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="v",
        )
        assert "ValidationIssue" in repr(vi)

    def test_to_json(self):
        vi = ValidationIssue(
            file="test.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="v", section="Guidance",
        )
        d = vi.to_json()
        assert d["file"] == "test.md"
        assert d["severity"] == "fail"

    def test_from_json(self):
        d = {
            "file": "test.md", "issue": "broken", "severity": "fail",
            "validator": "v",
        }
        vi = ValidationIssue.from_json(d)
        assert vi.severity == IssueSeverity.FAIL

    def test_json_round_trip(self):
        vi = ValidationIssue(
            file="test.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="v", section="Guidance", suggestion="Fix it",
        )
        restored = ValidationIssue.from_json(vi.to_json())
        assert restored == vi

    def test_to_markdown(self):
        vi = ValidationIssue(
            file="test.md", issue="Missing section",
            severity=IssueSeverity.FAIL, validator="check",
        )
        md = vi.to_markdown()
        assert "**FAIL**" in md
        assert "test.md" in md
        assert "Missing section" in md

    def test_validate_self_valid(self):
        vi = ValidationIssue(
            file="test.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="v",
        )
        assert vi.validate_self() == []

    def test_validate_self_empty_file(self):
        vi = ValidationIssue(
            file="", issue="broken", severity=IssueSeverity.FAIL,
            validator="v",
        )
        issues = vi.validate_self()
        assert len(issues) >= 1

    def test_is_valid(self):
        vi = ValidationIssue(
            file="test.md", issue="broken", severity=IssueSeverity.FAIL,
            validator="v",
        )
        assert vi.is_valid is True
```

**Step 2: Add builder**

Append to `tests/builders.py`:

```python
from wos.models.core import IssueSeverity, ValidationIssue


def make_validation_issue(**overrides) -> ValidationIssue:
    """Build a valid ValidationIssue with sensible defaults."""
    defaults = {
        "file": "context/test/example.md",
        "issue": "Example validation issue",
        "severity": IssueSeverity.WARN,
        "validator": "test_validator",
    }
    defaults.update(overrides)
    return ValidationIssue(**defaults)
```

**Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ddd_protocol.py::TestValidationIssueProtocol -v`
Expected: FAIL

**Step 4: Implement ValidationIssue DDD protocol**

Modify `wos/models/core.py:44-52`:

```python
class ValidationIssue(BaseModel):
    """A single validation issue found during document health checks."""

    model_config = ConfigDict(frozen=True)

    file: str
    issue: str
    severity: IssueSeverity
    validator: str
    section: Optional[str] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.file}: {self.issue}"

    def __repr__(self) -> str:
        return (
            f"ValidationIssue(file={self.file!r}, issue={self.issue!r}, "
            f"severity={self.severity.value!r}, validator={self.validator!r})"
        )

    def to_json(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> ValidationIssue:
        return cls.model_validate(data)

    def to_markdown(self) -> str:
        parts = [f"- **{self.severity.value.upper()}** `{self.file}`: {self.issue}"]
        if self.suggestion:
            parts.append(f"  - {self.suggestion}")
        return "\n".join(parts)

    def validate_self(self) -> list:
        issues: list[ValidationIssue] = []
        if not self.file and self.file != "":
            pass  # file can be empty string for non-file-specific issues
        if not self.issue.strip():
            issues.append(ValidationIssue(
                file="", issue="ValidationIssue has empty issue text",
                severity=IssueSeverity.FAIL, validator="validation_issue_self",
            ))
        return issues

    @property
    def is_valid(self) -> bool:
        return len(self.validate_self()) == 0
```

**Step 5: Run tests to verify pass**

Run: `python3 -m pytest tests/test_ddd_protocol.py -v`
Expected: ALL PASS

**Step 6: Run full suite, commit**

Run: `python3 -m pytest tests/ -v`

```bash
git add wos/models/core.py tests/test_ddd_protocol.py tests/builders.py
git commit -m "feat: enrich ValidationIssue with DDD protocol (frozen, str, json, markdown, validate_self)"
```

---

### Task 3: Enrich DocumentSection (with line number fields)

**Files:**
- Modify: `wos/models/core.py:58-70`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)

**Step 1: Add DocumentSection protocol tests**

Append to `tests/test_ddd_protocol.py`:

```python
from wos.models.core import DocumentSection


class TestDocumentSectionProtocol:
    def test_frozen_immutable(self):
        import pytest
        s = DocumentSection(name="Guidance", content="Use guidelines.")
        with pytest.raises(Exception):
            s.name = "Other"

    def test_frozen_hashable(self):
        s = DocumentSection(name="Guidance", content="Use guidelines.")
        assert s in {s}

    def test_equality(self):
        a = DocumentSection(name="Guidance", content="Use guidelines.")
        b = DocumentSection(name="Guidance", content="Use guidelines.")
        assert a == b

    def test_str(self):
        s = DocumentSection(name="Guidance", content="Use these guidelines for work.")
        result = str(s)
        assert "Guidance" in result
        assert "words" in result.lower()

    def test_to_json(self):
        s = DocumentSection(name="Guidance", content="Content here.")
        d = s.to_json()
        assert d["name"] == "Guidance"
        assert d["content"] == "Content here."

    def test_from_json(self):
        d = {"name": "Guidance", "content": "Content here."}
        s = DocumentSection.from_json(d)
        assert s.name == "Guidance"

    def test_json_round_trip(self):
        original = DocumentSection(name="Guidance", content="Content here.")
        restored = DocumentSection.from_json(original.to_json())
        assert restored == original

    def test_to_markdown(self):
        s = DocumentSection(name="Guidance", content="Use guidelines.")
        md = s.to_markdown()
        assert md.startswith("## Guidance")
        assert "Use guidelines." in md

    def test_line_number_fields_default_none(self):
        s = DocumentSection(name="Guidance", content="Content.")
        assert s.line_start is None
        assert s.line_end is None

    def test_line_number_fields_populated(self):
        s = DocumentSection(
            name="Guidance", content="Content.",
            line_start=10, line_end=15,
        )
        assert s.line_start == 10
        assert s.line_end == 15

    def test_validate_self_valid(self):
        s = DocumentSection(name="Guidance", content="Has content.")
        assert s.validate_self() == []

    def test_is_valid(self):
        s = DocumentSection(name="Guidance", content="Has content.")
        assert s.is_valid is True

    def test_get_estimated_tokens(self):
        s = DocumentSection(name="Guidance", content="Some content here.")
        tokens = s.get_estimated_tokens()
        assert isinstance(tokens, int)
        assert tokens > 0
```

**Step 2: Add builder**

Append to `tests/builders.py`:

```python
from wos.models.core import DocumentSection


def make_document_section(**overrides) -> DocumentSection:
    """Build a valid DocumentSection with sensible defaults."""
    defaults = {
        "name": "Guidance",
        "content": "Use these guidelines for effective implementation.",
    }
    defaults.update(overrides)
    return DocumentSection(**defaults)
```

**Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ddd_protocol.py::TestDocumentSectionProtocol -v`

**Step 4: Implement DocumentSection DDD protocol**

Modify `wos/models/core.py:58-70`:

```python
class DocumentSection(BaseModel):
    """A single H2 section within a document."""

    model_config = ConfigDict(frozen=True)

    name: str
    content: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None

    def __str__(self) -> str:
        return f"## {self.name} ({self.word_count} words)"

    def __repr__(self) -> str:
        lines = f", lines {self.line_start}-{self.line_end}" if self.line_start else ""
        return f"DocumentSection(name={self.name!r}, words={self.word_count}{lines})"

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + 1 if self.content else 0

    def to_json(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> DocumentSection:
        return cls.model_validate(data)

    def to_markdown(self) -> str:
        return f"## {self.name}\n\n{self.content}"

    def get_estimated_tokens(self) -> int:
        return len(self.name) // 4 + 2 + len(self.content) // 4

    def validate_self(self) -> list:
        from wos.models.core import ValidationIssue, IssueSeverity
        issues: list[ValidationIssue] = []
        if not self.name.strip():
            issues.append(ValidationIssue(
                file="", issue="Section name is blank",
                severity=IssueSeverity.FAIL, validator="document_section_name",
            ))
        return issues

    @property
    def is_valid(self) -> bool:
        return len(self.validate_self()) == 0
```

**Step 5: Run tests, verify pass, run full suite**

Run: `python3 -m pytest tests/test_ddd_protocol.py -v && python3 -m pytest tests/ -v`

**Step 6: Commit**

```bash
git add wos/models/core.py tests/test_ddd_protocol.py tests/builders.py
git commit -m "feat: enrich DocumentSection with DDD protocol (frozen, line numbers, str, json, markdown)"
```

---

### Task 4: Enrich SectionSpec

**Files:**
- Modify: `wos/models/frontmatter.py:138-143`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)

**Follow the same TDD pattern as Tasks 1-3:**

1. Write tests for: frozen, hashable, equality, `__str__` (format: `"Guidance @1"`), `__repr__`, `to_json`, `from_json`, json round-trip, `validate_self` (position > 0), `is_valid`, builder
2. Add `make_section_spec()` to `tests/builders.py` with defaults `name="Guidance", position=1`
3. Run tests, verify fail
4. Implement: add `model_config = ConfigDict(frozen=True)`, add `__str__`, `__repr__`, `to_json`, `from_json`, `validate_self`, `is_valid` to `SectionSpec` in `wos/models/frontmatter.py`
5. Add `from pydantic import BaseModel, ConfigDict, Field, field_validator` to frontmatter.py imports
6. Run tests, verify pass, run full suite
7. Commit: `"feat: enrich SectionSpec with DDD protocol"`

**`__str__` format:** `f"{self.name} @{self.position}"` (e.g., "Guidance @1")

**`validate_self` checks:** position >= 1, name not blank

---

### Task 5: Enrich SizeBounds

**Files:**
- Modify: `wos/models/frontmatter.py:182-186`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)

**Follow the same TDD pattern:**

1. Tests for: frozen, hashable, equality, `__str__` (format: `"10-500 lines"` or `"10+ lines"` if no max), `__repr__`, `to_json`, `from_json`, `validate_self` (min > 0, max >= min if set), `is_valid`, builder
2. Builder defaults: `min_lines=10, max_lines=500`
3. Implement on `SizeBounds` in `wos/models/frontmatter.py`
4. Commit: `"feat: enrich SizeBounds with DDD protocol"`

**`__str__` format:** `f"{self.min_lines}-{self.max_lines} lines"` or `f"{self.min_lines}+ lines"` if `max_lines is None`

---

## Phase 2: Verification Result Types

### Task 6: Migrate VerificationResult to Pydantic

**Files:**
- Modify: `wos/source_verification.py:99-119`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)
- Modify: `tests/test_source_verification.py` (fix any `asdict()` calls)

**Step 1: Add protocol tests**

Test: frozen, hashable, equality, `__str__` (format: `"ok: https://example.com"`), `__repr__`, `to_json`/`from_json` round-trip, `validate_self`, `is_valid`, builder.

**Step 2: Add builder**

`make_verification_result()` with defaults: `url="https://example.com", cited_title="Example", http_status=200, page_title="Example Page", title_match=True, action="ok", reason="Title matches"`

**Step 3: Migrate from `@dataclass` to Pydantic `BaseModel`**

Replace in `wos/source_verification.py`:

```python
class VerificationResult(BaseModel):
    """Result of verifying a single source URL."""

    model_config = ConfigDict(frozen=True)

    url: str
    cited_title: str
    http_status: Optional[int]
    page_title: Optional[str]
    title_match: Optional[bool]
    action: str  # "ok" | "removed" | "flagged"
    reason: str

    def __str__(self) -> str:
        return f"{self.action}: {self.url}"

    def __repr__(self) -> str:
        return f"VerificationResult(action={self.action!r}, url={self.url!r}, reason={self.reason!r})"

    def to_json(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> VerificationResult:
        return cls.model_validate(data)

    def validate_self(self) -> list:
        from wos.models.core import ValidationIssue, IssueSeverity
        issues: list[ValidationIssue] = []
        if self.action not in ("ok", "removed", "flagged"):
            issues.append(ValidationIssue(
                file="", issue=f"Invalid action: {self.action}",
                severity=IssueSeverity.FAIL, validator="verification_result_action",
            ))
        return issues

    @property
    def is_valid(self) -> bool:
        return len(self.validate_self()) == 0
```

**Step 4: Fix callers**

In `wos/source_verification.py`, replace `from dataclasses import asdict, dataclass` with `from pydantic import BaseModel, ConfigDict`. Change `asdict(r)` calls (line ~413) to `r.to_json()`.

**Step 5: Run full test suite, fix regressions, commit**

```bash
git commit -m "feat: migrate VerificationResult to Pydantic with DDD protocol"
```

---

### Task 7: Migrate ReachabilityResult to Pydantic

**Files:**
- Modify: `wos/source_verification.py:113-120`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)

**Same pattern as Task 6.** Replace `@dataclass` with Pydantic `BaseModel` + `frozen=True`.

**`__str__` format:** `f"{'reachable' if self.reachable else 'unreachable'}: {self.url}"`

Builder defaults: `url="https://example.com", http_status=200, reachable=True, reason="OK", final_url="https://example.com"`

Commit: `"feat: migrate ReachabilityResult to Pydantic with DDD protocol"`

---

## Phase 3: Line Number Tracking

### Task 8: Update _split_markdown to compute line numbers

**Files:**
- Modify: `wos/models/parsing.py:34-80`
- Modify: `wos/models/documents.py:24-31` (add frontmatter_line_end, title_line fields)
- Modify: `tests/test_ddd_protocol.py` (append)

**Step 1: Add line number tests**

```python
from wos.models.parsing import parse_document


class TestLineNumberTracking:
    def test_frontmatter_line_end(self):
        md = (
            "---\n"                  # line 1
            "document_type: plan\n"  # line 2
            'description: "Implementation plan for a four-type document system"\n'
            "last_updated: 2026-02-17\n"
            "---\n"                  # line 5
            "\n"
            "# My Plan\n"           # line 7
            "\n"
            "## Objective\n"        # line 9
            "\n"
            "Goal here.\n"
            "\n"
            "## Context\n"          # line 13
            "\n"
            "Background.\n"
            "\n"
            "## Steps\n"            # line 17
            "\n"
            "1. Do stuff.\n"
            "\n"
            "## Verification\n"     # line 21
            "\n"
            "- It works.\n"
        )
        doc = parse_document("artifacts/plans/2026-02-17-plan.md", md)
        assert doc.frontmatter_line_end == 5
        assert doc.title_line == 7

    def test_section_line_numbers(self):
        md = (
            "---\n"
            "document_type: plan\n"
            'description: "Implementation plan for a four-type document system"\n'
            "last_updated: 2026-02-17\n"
            "---\n"
            "\n"
            "# My Plan\n"
            "\n"
            "## Objective\n"        # line 9
            "\n"
            "Goal here.\n"
            "\n"
            "## Context\n"          # line 13
            "\n"
            "Background.\n"
            "\n"
            "## Steps\n"            # line 17
            "\n"
            "1. Do stuff.\n"
            "\n"
            "## Verification\n"     # line 21
            "\n"
            "- It works.\n"
        )
        doc = parse_document("artifacts/plans/2026-02-17-plan.md", md)
        objective = doc.get_section("Objective")
        assert objective is not None
        assert objective.line_start == 9

        verification = doc.get_section("Verification")
        assert verification is not None
        assert verification.line_start == 21
```

**Step 2: Run tests, verify fail**

**Step 3: Implement line number tracking**

In `wos/models/documents.py`, add fields to `BaseDocument`:

```python
class BaseDocument(BaseModel):
    path: str
    frontmatter: Frontmatter
    title: str
    sections: List[DocumentSection]
    raw_content: str
    frontmatter_line_end: Optional[int] = None
    title_line: Optional[int] = None
```

In `wos/models/parsing.py`, update `_split_markdown()`:

```python
def _split_markdown(content):
    # ... existing frontmatter extraction ...

    fm_line_end = content[:fm_match.end()].count('\n')

    body = content[fm_match.end():]
    body_start_line = fm_line_end + 1

    # Extract title
    h1_match = _H1_RE.search(body)
    title = h1_match.group(1).strip() if h1_match else ""
    title_line = body_start_line + body[:h1_match.start()].count('\n') if h1_match else None

    # Extract sections with line numbers
    sections = []
    h2_matches = list(_H2_RE.finditer(body))
    for i, m in enumerate(h2_matches):
        section_name = m.group(1).strip()
        start = m.end()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(body)
        line_start = body_start_line + body[:m.start()].count('\n')
        line_end = body_start_line + body[:end].rstrip().count('\n')
        sections.append(DocumentSection(
            name=section_name,
            content=body[start:end].strip(),
            line_start=line_start,
            line_end=line_end,
        ))

    return frontmatter_dict, title, sections, content, fm_line_end, title_line
```

Update `parse_document()` to pass the new fields through.

**Step 4: Run tests, fix, commit**

```bash
git commit -m "feat: add line number tracking to DocumentSection and BaseDocument"
```

---

## Phase 4: Document Hierarchy

### Task 9: Enrich BaseDocument with DDD protocol

**Files:**
- Modify: `wos/models/documents.py:24-133`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)

**Add to BaseDocument:**

1. `__str__` — `f"{self.title} ({self.document_type.value})"`
2. `__repr__` — `f"BaseDocument(path={self.path!r}, type={self.document_type.value!r})"`
3. `__len__` — `len(self.sections)`
4. `__iter__` — `iter(self.sections)`
5. `__contains__` — `item in self.section_names` (for strings) or `item in self.sections` (for DocumentSection)
6. `area_name` property — extracts area from path via `re.match(r"context/([^/]+)/", self.path)`
7. `from_markdown(cls, path, content)` classmethod — wraps `parse_document()`
8. `to_markdown()` — renders full document with YAML frontmatter + title + sections
9. Rename `validate_structure()` to `validate_self()` (keep `validate_structure` as alias for backward compat)
10. Add `is_valid` property

**Builder:** `make_document()` in `tests/builders.py` that builds a minimal valid plan document (simplest type). Uses inline markdown string and `parse_document()`.

**Commit:** `"feat: enrich BaseDocument with DDD protocol (str, collection, area_name, from/to_markdown)"`

---

### Tasks 10-14: Enrich Document Subclasses

Each document subclass (TopicDocument, OverviewDocument, ResearchDocument, PlanDocument, NoteDocument) follows the same pattern:

1. Override `to_markdown()` to render type-specific frontmatter (absorb from `templates.py`)
2. Rename `validate_structure()` to `validate_self()` (keep alias)
3. Add type-specific builder to `tests/builders.py`
4. Add protocol tests

**Task 10:** TopicDocument — absorb `templates.render_topic()`, `make_topic_document()` builder
**Task 11:** OverviewDocument — absorb `templates.render_overview()`, `make_overview_document()` builder
**Task 12:** ResearchDocument — absorb `templates.render_research()`, `make_research_document()` builder
**Task 13:** PlanDocument — absorb `templates.render_plan()`, `make_plan_document()` builder
**Task 14:** NoteDocument — absorb `templates.render_note()`, `make_note_document()` builder

Each commit: `"feat: enrich {TypeName} with DDD protocol (to_markdown, validate_self, builder)"`

---

## Phase 5: Aggregates

### Task 15: Enrich ContextArea

**Files:**
- Modify: `wos/models/context_area.py`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)

**Add:**
1. `__str__` — `f"{self.display_name} ({len(self.topics)} topics)"`
2. `__repr__` — `f"ContextArea(name={self.name!r}, topics={len(self.topics)})"`
3. `__len__` — `len(self.topics)`
4. `__iter__` — `iter(self.topics)`
5. `__contains__` — check topic name or title
6. `from_documents(cls, docs)` classmethod — absorbs `_build_context_areas()` logic
7. `to_json()` — dict with name, overview_path, topics list
8. Rename `validate()` to `validate_self()` (keep alias)
9. `is_valid` property
10. `make_context_area()` builder

Commit: `"feat: enrich ContextArea with DDD protocol (collection, from_documents, validate_self)"`

---

### Task 16: Enrich HealthReport

**Files:**
- Modify: `wos/models/health_report.py`
- Modify: `tests/test_ddd_protocol.py` (append)
- Modify: `tests/builders.py` (append)

**Add:**
1. `__str__` — absorbs `format_summary()` from `formatting.py` (without ANSI colors)
2. `__repr__` — `f"HealthReport(status={self.status.value!r}, files={self.files_checked}, issues={len(self.issues)})"`
3. `format_detailed(color=False)` — absorbs `format_detailed()` from `formatting.py`
4. `format_summary(color=False)` — absorbs `format_summary()` from `formatting.py`
5. `__len__` — `len(self.issues)`
6. `__iter__` — `iter(self.issues)`
7. `__contains__` — check if ValidationIssue is in issues
8. `from_json(cls, data)` classmethod
9. `is_valid` property (True if status is PASS)
10. `make_health_report()` builder

Commit: `"feat: enrich HealthReport with DDD protocol (absorb formatting, collection)"`

---

## Phase 6: Cleanup & Deduplication

### Task 17: Thin out validators.py

**Files:**
- Modify: `wos/validators.py`

Make `validate_document(doc)` delegate to `doc.validate_self()`. Keep as backward compat wrapper. Remove standalone validator functions that are now inline in document subclasses.

Commit: `"refactor: thin validators.py to backward compat wrapper around doc.validate_self()"`

---

### Task 18: Thin out formatting.py

**Files:**
- Modify: `wos/formatting.py`
- Modify: `scripts/check_health.py`

Make `format_summary()` and `format_detailed()` accept either dict or HealthReport. Delegate to HealthReport methods when given an object. Update `check_health.py` to call `report.format_summary()` directly.

Commit: `"refactor: thin formatting.py, check_health.py uses HealthReport methods directly"`

---

### Task 19: Thin out templates.py

**Files:**
- Modify: `wos/templates.py`

Make `render_*()` functions delegate to document subclass `to_markdown()`. Keep as backward compat wrappers.

Commit: `"refactor: thin templates.py to backward compat wrappers around doc.to_markdown()"`

---

### Task 20: Remove duplicates

**Files:**
- Modify: `wos/scaffold.py:115-120` — remove `_display_name()`, import from ContextArea
- Modify: `wos/token_budget.py:78-81` — remove `_extract_area()`, use `doc.area_name`
- Modify: `wos/cross_validators.py:220-246` — remove `_build_context_areas()`, use `ContextArea.from_documents()`

Commit: `"refactor: remove duplicate utility functions, use domain object methods"`

---

### Task 21: Final CLAUDE.md update

**Files:**
- Modify: `CLAUDE.md`

Verify the Domain Model Conventions section is accurate and reflects the actual implementation. Update any conventions that changed during implementation.

Commit: `"docs: finalize Domain Model Conventions in CLAUDE.md"`

---

## Verification Checklist

After all tasks:

1. `python3 -m pytest tests/ -v` — all tests pass
2. `ruff check wos/ tests/ scripts/` — no lint errors (if ruff available)
3. Every domain object has: `__str__`, `__repr__`, `to_json`, `from_json`, `validate_self`, `is_valid`
4. Value objects have `frozen=True` and are hashable
5. `tests/builders.py` has `make_*()` for every domain object
6. `tests/test_ddd_protocol.py` covers the full DDD protocol for every object
7. `formatting.py` functions are thin wrappers or deleted
8. `validators.py` `validate_document()` delegates to `doc.validate_self()`
9. `templates.py` render functions delegate to `doc.to_markdown()`
10. No duplicate utility functions remain
