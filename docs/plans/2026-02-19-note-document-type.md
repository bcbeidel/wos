# Note Document Type Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `note` document type with minimal frontmatter (`document_type` + `description`) that WOS tolerates anywhere without failing validation or appearing in the manifest.

**Architecture:** Extend the existing Pydantic discriminated union with a 5th type. `NoteFrontmatter` is standalone (does not extend `FrontmatterBase` since that requires `last_updated`). Dispatch tables get minimal entries: empty sections, loose size bounds, no directory pattern. Only the `check_title_heading` validator applies.

**Tech Stack:** Python 3.9, Pydantic v2, pytest

---

### Task 1: Add NoteFrontmatter model and enum value

**Files:**
- Modify: `wos/document_types.py:21-26` (enum), `wos/document_types.py:118-133` (models + union)
- Test: `tests/test_document_types.py`

**Step 1: Write the failing test**

Add to `tests/test_document_types.py`:

```python
def _note_md(
    *,
    description="Personal notes on effective meeting facilitation techniques",
    extra_fm="",
) -> str:
    return (
        "---\n"
        "document_type: note\n"
        f'description: "{description}"\n'
        f"{extra_fm}"
        "---\n"
        "\n"
        "# Meeting Facilitation\n"
        "\n"
        "Some content here.\n"
    )


class TestNoteDocument:
    def test_note_parses(self):
        doc = parse_document("notes/meeting-facilitation.md", _note_md())
        assert doc.document_type == DocumentType.NOTE
        assert doc.frontmatter.description == (
            "Personal notes on effective meeting facilitation techniques"
        )

    def test_note_minimal_frontmatter(self):
        """Note requires only document_type and description."""
        doc = parse_document("notes/test.md", _note_md())
        assert not hasattr(doc.frontmatter, "last_updated")
        assert not hasattr(doc.frontmatter, "sources")

    def test_note_with_tags(self):
        md = _note_md(extra_fm='tags:\n  - meetings\n  - facilitation\n')
        doc = parse_document("notes/test.md", md)
        assert doc.frontmatter.tags == ["meetings", "facilitation"]

    def test_note_with_related(self):
        md = _note_md(extra_fm='related:\n  - context/area/topic.md\n')
        doc = parse_document("notes/test.md", md)
        assert doc.frontmatter.related == ["context/area/topic.md"]

    def test_note_short_description_rejected(self):
        with pytest.raises(ValidationError):
            parse_document("notes/test.md", _note_md(description="Short"))

    def test_note_any_directory_accepted(self):
        """Notes can live anywhere — no directory pattern enforced."""
        for path in [
            "notes/test.md",
            "context/area/test.md",
            "artifacts/test.md",
            "reading/book.md",
            "recipes/pasta.md",
        ]:
            doc = parse_document(path, _note_md())
            assert doc.document_type == DocumentType.NOTE
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_document_types.py::TestNoteDocument -v`
Expected: FAIL — `DocumentType` has no `NOTE` member

**Step 3: Implement the model**

In `wos/document_types.py`:

1. Add `NOTE = "note"` to the `DocumentType` enum (after `PLAN = "plan"`, line 25)

2. Add `NoteFrontmatter` model after `PlanFrontmatter` (after line 120):

```python
class NoteFrontmatter(BaseModel):
    """Minimal frontmatter for generic notes — no structural requirements."""

    document_type: Literal["note"]
    description: str = Field(min_length=10)

    # Optional fields — same validation as other types
    tags: Optional[List[str]] = None
    related: Optional[List[str]] = None

    @field_validator("tags")
    @classmethod
    def tags_lowercase_hyphenated(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        if v is None:
            return v
        for tag in v:
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", tag):
                raise ValueError(
                    f"tag '{tag}' must be lowercase hyphenated "
                    f"(e.g., 'api-design', 'caching')"
                )
        return v
```

3. Add `NoteFrontmatter` to the `Frontmatter` discriminated union (line 125-133):

```python
Frontmatter = Annotated[
    Union[
        TopicFrontmatter,
        OverviewFrontmatter,
        ResearchFrontmatter,
        PlanFrontmatter,
        NoteFrontmatter,
    ],
    Field(discriminator="document_type"),
]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_document_types.py::TestNoteDocument -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add wos/document_types.py tests/test_document_types.py
git commit -m "feat: add note document type with minimal frontmatter (#5)"
```

---

### Task 2: Add dispatch table entries for note type

**Files:**
- Modify: `wos/document_types.py:147-202` (dispatch tables)
- Test: `tests/test_document_types.py`

**Step 1: Write the failing tests**

Add to `tests/test_document_types.py` inside `TestNoteDocument`:

```python
    def test_note_no_required_sections(self):
        doc = parse_document("notes/test.md", _note_md())
        assert doc.required_sections == []

    def test_note_size_bounds_minimal(self):
        doc = parse_document("notes/test.md", _note_md())
        assert doc.size_bounds.min_lines == 1
        assert doc.size_bounds.max_lines is None
```

Also add to the existing `TestDispatchTables` class:

```python
    def test_note_not_in_directory_patterns(self):
        assert DocumentType.NOTE not in DIRECTORY_PATTERNS
```

And add to the existing `TestTypeGroupings` class:

```python
    def test_note_not_in_any_group(self):
        assert DocumentType.NOTE not in CONTEXT_TYPES
        assert DocumentType.NOTE not in ARTIFACT_TYPES
        assert DocumentType.NOTE not in SOURCE_GROUNDED_TYPES
        assert DocumentType.NOTE not in FRESHNESS_TRACKED_TYPES
        assert DocumentType.NOTE not in DATE_PREFIX_TYPES
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_document_types.py::TestNoteDocument::test_note_no_required_sections tests/test_document_types.py::TestNoteDocument::test_note_size_bounds_minimal tests/test_document_types.py::TestDispatchTables::test_note_not_in_directory_patterns tests/test_document_types.py::TestTypeGroupings::test_note_not_in_any_group -v`
Expected: FAIL — KeyError on `SECTIONS[DocumentType.NOTE]`

**Step 3: Add dispatch table entries**

In `wos/document_types.py`:

1. Add to `SECTIONS` dict (after the PLAN entry, line 171):
```python
    DocumentType.NOTE: [],
```

2. Add to `OPTIONAL_SECTIONS` dict (after the TOPIC entry, line 178):
```python
    DocumentType.NOTE: {},
```

3. Add to `SIZE_BOUNDS` dict (after the PLAN entry, line 192):
```python
    DocumentType.NOTE: SizeBounds(min_lines=1),
```

4. Do NOT add to `DIRECTORY_PATTERNS`, `DATE_PREFIX_TYPES`, or any type grouping set.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_document_types.py -v`
Expected: ALL pass (existing + new)

**Step 5: Commit**

```bash
git add wos/document_types.py tests/test_document_types.py
git commit -m "feat: add dispatch table entries for note type (#5)"
```

---

### Task 3: Add minimal validators for note type

**Files:**
- Modify: `wos/validators.py:440-458` (dispatch table)
- Test: `tests/test_validators.py`

**Step 1: Write the failing tests**

Add a `_note_md` helper and `TestNoteValidation` class to `tests/test_validators.py`:

```python
def _note_md(
    *,
    description="Personal notes on effective meeting facilitation techniques",
) -> str:
    return (
        "---\n"
        "document_type: note\n"
        f'description: "{description}"\n'
        "---\n"
        "\n"
        "# Meeting Facilitation\n"
        "\n"
        "Some content here.\n"
    )


class TestNoteValidation:
    def test_clean_note_no_issues(self):
        doc = parse_document("notes/test.md", _note_md())
        issues = validate_document(doc)
        assert issues == []

    def test_note_missing_title_warns(self):
        md = (
            "---\n"
            "document_type: note\n"
            'description: "Personal notes on effective meeting facilitation"\n'
            "---\n"
            "\n"
            "Some content without a title.\n"
        )
        doc = parse_document("notes/test.md", md)
        issues = validate_document(doc)
        assert len(issues) == 1
        assert issues[0]["validator"] == "check_title_heading"

    def test_note_no_section_checks(self):
        """Notes should not get section presence/ordering checks."""
        md = (
            "---\n"
            "document_type: note\n"
            'description: "Personal notes on effective meeting facilitation"\n'
            "---\n"
            "\n"
            "# My Note\n"
            "\n"
            "## Random Section\n"
            "\n"
            "Content here.\n"
            "\n"
            "## Another Section\n"
            "\n"
            "More content.\n"
        )
        doc = parse_document("notes/test.md", md)
        issues = validate_document(doc)
        # No section presence/ordering issues since note has no requirements
        assert all(
            i["validator"] != "check_section_presence" for i in issues
        )
        assert all(
            i["validator"] != "check_section_ordering" for i in issues
        )
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_validators.py::TestNoteValidation -v`
Expected: FAIL — `test_clean_note_no_issues` will produce section/size/directory issues because the note type falls through to `_SHARED_VALIDATORS`

**Step 3: Add note validator entry**

In `wos/validators.py`, add to `VALIDATORS_BY_TYPE` dict (after the PLAN entry, line 457):

```python
    DocumentType.NOTE: [
        check_title_heading,
    ],
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_validators.py -v`
Expected: ALL pass (existing + new)

**Step 5: Commit**

```bash
git add wos/validators.py tests/test_validators.py
git commit -m "feat: add minimal validators for note type (#5)"
```

---

### Task 4: Add note template

**Files:**
- Modify: `wos/templates.py:148-160` (render function + dispatch table)
- Test: `tests/test_templates.py`

**Step 1: Write the failing test**

Add to `tests/test_templates.py`:

```python
class TestRenderNote:
    def test_round_trip(self):
        from wos.templates import render_note

        md = render_note("My Note", "Personal notes on a specific topic area")
        doc = parse_document("notes/test.md", md)
        assert doc.document_type == DocumentType.NOTE
        assert doc.frontmatter.description == (
            "Personal notes on a specific topic area"
        )
        assert doc.title == "My Note"

    def test_no_sections(self):
        from wos.templates import render_note

        md = render_note("My Note", "Personal notes on a specific topic area")
        doc = parse_document("notes/test.md", md)
        assert doc.sections == {}

    def test_dispatch_table_has_note(self):
        from wos.templates import TEMPLATES

        assert DocumentType.NOTE in TEMPLATES
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_templates.py::TestRenderNote -v`
Expected: FAIL — `render_note` does not exist

**Step 3: Implement render_note**

Add to `wos/templates.py` before the dispatch table (before line 151):

```python
def render_note(
    title: str,
    description: str,
) -> str:
    """Render a note document with minimal frontmatter and no sections."""
    return (
        "---\n"
        "document_type: note\n"
        f'description: "{_escape_yaml(description)}"\n'
        "---\n"
        "\n"
        f"# {title}\n"
    )
```

Add to the `TEMPLATES` dispatch table:

```python
    DocumentType.NOTE: render_note,
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_templates.py -v`
Expected: ALL pass (existing + new)

**Step 5: Commit**

```bash
git add wos/templates.py tests/test_templates.py
git commit -m "feat: add note template with minimal frontmatter (#5)"
```

---

### Task 5: Add note entry to tier2 triggers

**Files:**
- Modify: `wos/tier2_triggers.py:238-253`
- Test: `tests/test_tier2_triggers.py`

**Step 1: Write the failing test**

Add to `tests/test_tier2_triggers.py`:

```python
class TestNoteTriggers:
    def test_note_has_triggers(self):
        from wos.tier2_triggers import TIER2_TRIGGERS_BY_TYPE

        assert DocumentType.NOTE in TIER2_TRIGGERS_BY_TYPE

    def test_note_triggers_empty(self):
        """Notes should have no tier2 triggers."""
        from wos.tier2_triggers import TIER2_TRIGGERS_BY_TYPE

        assert TIER2_TRIGGERS_BY_TYPE[DocumentType.NOTE] == []
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tier2_triggers.py::TestNoteTriggers -v`
Expected: FAIL — KeyError on `DocumentType.NOTE`

**Step 3: Add empty trigger list**

In `wos/tier2_triggers.py`, add to `TIER2_TRIGGERS_BY_TYPE` dict (after the PLAN entry):

```python
    DocumentType.NOTE: [],
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tier2_triggers.py -v`
Expected: ALL pass

**Step 5: Commit**

```bash
git add wos/tier2_triggers.py tests/test_tier2_triggers.py
git commit -m "feat: add empty tier2 triggers for note type (#5)"
```

---

### Task 6: Verify cross-validators and discovery skip notes

**Files:**
- Test: `tests/test_cross_validators.py`
- Test: `tests/test_discovery.py`

**Step 1: Write verification tests**

Add to `tests/test_cross_validators.py`:

```python
class TestNotesCrossValidation:
    def test_naming_conventions_skip_notes(self):
        """check_naming_conventions should not flag note files."""
        from wos.cross_validators import check_naming_conventions

        md = (
            "---\n"
            "document_type: note\n"
            'description: "Personal notes on meeting facilitation techniques"\n'
            "---\n"
            "\n"
            "# My Note\n"
        )
        doc = parse_document("WEIRD_PATH/My File.md", md)
        issues = check_naming_conventions([doc], "/tmp")
        assert issues == []
```

**Step 2: Run tests**

Run: `pytest tests/test_cross_validators.py::TestNotesCrossValidation -v`
Expected: PASS — `check_naming_conventions` already scopes to TOPIC and OVERVIEW types (line 191), so notes are implicitly skipped.

If this test FAILS, it means `check_naming_conventions` needs to be updated to skip notes. Add a guard: `if doc.document_type not in {DocumentType.TOPIC, DocumentType.OVERVIEW}: continue`

**Step 3: Commit**

```bash
git add tests/test_cross_validators.py
git commit -m "test: verify cross-validators skip note type (#5)"
```

---

### Task 7: Full test suite + version bump + changelog

**Files:**
- Modify: `pyproject.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- Modify: `CHANGELOG.md`

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: ALL pass (305 + ~15 new tests)

**Step 2: Bump version to 0.1.8**

In all three files, change `0.1.7` to `0.1.8`:
- `pyproject.toml`: `version = "0.1.8"`
- `.claude-plugin/plugin.json`: `"version": "0.1.8"`
- `.claude-plugin/marketplace.json`: `"version": "0.1.8"`

**Step 3: Add changelog entry**

Add between `## [Unreleased]` and `## [0.1.7]` in `CHANGELOG.md`:

```markdown
## [0.1.8] - 2026-02-19

### Added

- **Note document type** (`document_type: note`): A generic document type with
  minimal frontmatter requirements (`document_type` + `description` only). Notes
  can live anywhere in the repo without failing health checks, have no required
  sections, no directory constraints, and are excluded from the CLAUDE.md
  manifest. Useful for work products that don't fit the topic/overview/research/
  plan schema — decision records, reading notes, templates, personal docs, etc.
  ([#5](https://github.com/bcbeidel/wos/issues/5))
```

Add link reference at bottom:
```
[0.1.8]: https://github.com/bcbeidel/wos/releases/tag/v0.1.8
```

**Step 4: Run full test suite again**

Run: `pytest tests/ -v`
Expected: ALL pass

**Step 5: Commit**

```bash
git add pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "chore: bump version to 0.1.8 (#5)"
```

---
