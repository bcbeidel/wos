---
name: Stdlib Migration and Validator Refactoring Design
description: Design for issue #68 — stdlib-only migration, merged checks with warn/fail severity, preamble-preserving indexes, LLM-friendly output, /distill skill
type: plan
related:
  - docs/plans/2026-02-22-simplification-design.md
---

# Stdlib Migration & Validator Refactoring Design

**Issue:** #68 — Align WOS with dual-audience research
**Branch:** `feat/stdlib-and-checks`
**Version:** 0.3.6 → 0.4.0
**Approach:** Single branch, three phases, granular commits, one PR

## Problem

1. Python scripts fail for most users (PEP 668 blocks pip install, no plugin install hooks)
2. No pathway from research artifacts (2000-5000 words) to context files (200-800 words)
3. All validation issues are `severity: "fail"` — no distinction between broken and drifted

## Phase 1: Stdlib Migration

### 1.1 Custom Frontmatter Parser (`wos/frontmatter.py`)

Two-layer architecture:

**Layer 1 — `parse_frontmatter(text: str) -> tuple[dict, str]`**
- Finds `---` delimiters, extracts YAML region and body content
- Line-by-line parser for restricted YAML subset:
  - `key: value` → `{"key": "value"}` (all values as strings, no type coercion)
  - `key:` (no value) → `{"key": None}`
  - `- item` under a key → `{"key": ["item1", "item2"]}`
  - No nested dicts, no booleans, no numbers, no dates
- Returns `(frontmatter_dict, body_content)`
- Raises `ValueError` on missing/malformed delimiters

**Layer 2 — validation stays in `validators.py`**
- `check_frontmatter()` enforces types after parsing
- Dict-format sources flagged as `warn`

### 1.2 Migrate `document.py`

- Replace `import yaml` with `from wos.frontmatter import parse_frontmatter`
- `parse_document()` calls `parse_frontmatter()` instead of `yaml.safe_load()`
- Drop `Document.extra` field — unknown frontmatter keys ignored by parser
- `_KNOWN_FIELDS` set stays for field extraction

### 1.3 Replace `requests` with `urllib` in `url_checker.py`

| Current | Replacement |
|---------|-------------|
| `requests.head(url, timeout=10, headers=h)` | `urllib.request.urlopen(Request(url, method='HEAD', headers=h), timeout=10)` |
| `requests.get(url, timeout=10, headers=h)` | `urllib.request.urlopen(Request(url, headers=h), timeout=10)` |
| `response.status_code` | `response.status` or `HTTPError.code` |
| `requests.ConnectionError` | `urllib.error.URLError` |
| `requests.Timeout` | `urllib.error.URLError` (timeout reason) |

Redirects: `urllib.request.urlopen()` follows redirects automatically via `HTTPRedirectHandler` (301, 302, 307, 308). Default limit of 10 redirects. Sufficient for reachability checking.

HEAD → 405 fallback: catch `HTTPError`, check `.code == 405`, retry with GET.

### 1.4 Remove Dependencies

```toml
# pyproject.toml
dependencies = []  # Was: pydantic>=2.0, pyyaml>=6.0, requests>=2.28

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.4"]
```

- `pydantic`: already unused (dead dependency)
- `pyyaml`: replaced by custom parser
- `requests`: replaced by urllib

### 1.5 Simplify `research_protocol.py`

- Remove `main()`, argparse import, `__main__` block (~25 lines)
- Keep dataclasses (`SearchEntry`, `SearchProtocol`) and formatters
- Keep `_protocol_from_json()` for programmatic use
- Update `/wos:research` skill to format protocol tables inline (more token-efficient)

## Phase 2: Validator & Output Refactoring

### 2.1 Merge Frontmatter Checks + Warn/Fail Severity

Merge `check_frontmatter()` and `check_research_sources()` into single `check_frontmatter()`:

```python
def check_frontmatter(doc: Document, context_path: str = "context") -> list[dict]:
    issues = []

    # FAIL: required fields
    if not doc.name or not doc.name.strip(): ...
    if not doc.description or not doc.description.strip(): ...

    # FAIL: research docs must have sources
    if doc.type == "research" and not doc.sources: ...

    # WARN: source items should be strings, not dicts
    for idx, source in enumerate(doc.sources):
        if isinstance(source, dict): ...

    # WARN: context files should have related
    if doc.path.startswith(context_path + "/") and not doc.related: ...

    return issues
```

Severity semantics:

| Severity | Meaning | Exit code |
|----------|---------|-----------|
| `fail` | Broken — must fix | 1 |
| `warn` | Drift — fix when convenient | 0 |

Add `--strict` flag: exit 1 on any issue.

### 2.2 New `check_content()` Function

```python
def check_content(doc, context_path="context", max_words=800):
    """Warn when context files exceed word count threshold."""
```

- Only checks context files (not artifacts)
- Skips `_index.md`
- Configurable via `--context-max-words N`

### 2.3 Preamble-Preserving Index Generation

- New `_extract_preamble(index_path: Path) -> Optional[str]` — reads existing `_index.md`, returns text between heading and first `|` table row
- `generate_index()` accepts optional `preamble` parameter
- When regenerating, reads existing preamble first and preserves it
- New warn-level check: index exists but has no preamble → `"warn: Index has no area description"`
- `--fix` notes: `"suggest: add 1-2 sentence area description to _index.md"`

### 2.4 LLM-Friendly Script Output

Before:
```
[FAIL] /abs/path/context/api/auth.md: Frontmatter 'name' is empty
2 issues found.
```

After:
```
2 fail, 0 warn across 47 files

file                              | sev  | issue
context/api/auth.md               | fail | Frontmatter 'name' is empty
```

Rules:
- Summary line first
- Relative paths only
- Table format
- `--json` unchanged
- `reindex.py`: `wrote 12 index files`
- Exit code: 1 if any `fail`, 0 if only `warn` (unless `--strict`)

### 2.5 Merge `validate.py` into `audit.py`

- `audit.py [FILE]` — optional positional arg for single-file mode
- Without `FILE`: runs `validate_project()`
- With `FILE`: runs `validate_file()`
- Remove `scripts/validate.py`
- Update skill references

## Phase 3: Skill Layer

### 3.1 `/wos:create` Updates

**Area creation:**
- Ask for 1-2 sentence area description
- Write as preamble in `_index.md` above file table

**Document creation — soft guardrails:**
1. Word count advisory — report count, suggest splitting if >800 words
2. Related-field prompting — scan existing files, suggest `related:` candidates
3. Bidirectional linking prompt — ask if referenced file should link back

### 3.2 New `/wos:distill` Skill

Structure:
```
skills/distill/
  SKILL.md
  references/
    distillation-guidelines.md
```

Workflow:
1. **Input** — User provides research artifact path (or skill finds most recent)
2. **Analyze** — Read research doc, identify discrete findings with confidence levels
3. **Propose** — Present distillation plan: findings → files, target area, filenames. User approves.
4. **Generate** — For each approved file:
   - 200-800 word context file with proper frontmatter
   - Key insight top, detail middle, takeaway bottom
   - `related:` linking back to source research + sibling files
   - Carry forward relevant `sources:` URLs
5. **Integrate** — Run reindex, update research artifact's `related:` to link forward

Key constraint: user controls granularity.

## Housekeeping

- Version bump: 0.3.6 → 0.4.0 across `pyproject.toml`, `plugin.json`, `marketplace.json`
- Update CLAUDE.md: new module (`frontmatter.py`), removed script (`validate.py`), new skill (`/distill`), updated check descriptions

## Breaking Changes

- `dependencies` goes from 3 packages to empty
- Audit output format changes (`[FAIL] path: msg` → summary + table)
- Exit code: 0 for warn-only (was 1 for any issue). `--strict` restores old behavior.
- `scripts/validate.py` removed (merged into `audit.py`)
- `Document.extra` field removed

## Test Strategy

- Port all existing tests to work with new implementations
- Custom parser: test against every frontmatter pattern in codebase + edge cases
- urllib: re-mock all `test_url_checker.py` tests against `urllib.request.urlopen`
- Merged checks: test warn vs fail severity, context_path parameter
- Preamble: test preservation across regeneration
- Output format: test new table format in `test_audit.py`
