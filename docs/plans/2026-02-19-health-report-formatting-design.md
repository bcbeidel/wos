# Health Report Formatting Design

**Date:** 2026-02-19
**Issue:** #15
**Branch:** `issue/15-health-report-formatting`

## Problem

The `/wos:health` skill outputs raw JSON from `scripts/check_health.py`, and the
skill workflow instructs the LLM to parse, group, and format the results. This
means health report presentation is non-deterministic, CI pipelines get only
JSON, and the LLM spends tokens reformatting structured data that Python already
has full knowledge of.

## Design Decisions

- **New `wos/formatting.py` module.** Pure functions that take the existing
  report dict and return formatted strings. Importable and testable without
  subprocess.
- **Text is the new default.** JSON moves behind `--json`. Breaking change for
  stdout parsers, but exit code behavior unchanged.
- **Two text modes: summary and detailed.** Summary is one-line-per-issue
  (compact, CI-friendly). Detailed groups by severity with suggestions and
  per-area token budget breakdown.
- **Basic ANSI color.** Auto-detect TTY. Red for FAIL, yellow for WARN, dim
  for INFO, green for PASS. `--no-color` flag to disable. Only severity labels
  and the status word are colored.
- **Skill workflows simplified.** Health-check workflow runs the command and
  shows output directly — no more "parse JSON and group by severity"
  instructions.

## Output Formats

### Summary (default)

```
Health: WARN (3 issues in 12 files)

  FAIL  context/area/topic.md        Missing required section: ## Guidance
  WARN  context/area/_overview.md    Topic not listed in overview: new-topic.md
  INFO  context/other/old-topic.md   Last validated 45 days ago

Token budget: 28,500 / 40,000
```

Clean run:

```
Health: PASS (0 issues in 5 files)

Token budget: 1,200 / 40,000
```

Issues sorted: fail first, then warn, then info. Within each severity, sorted
by file path.

### Detailed (`--detailed`)

```
Health: WARN (3 issues in 12 files)

Failures (1)
  context/area/topic.md
    Missing required section: ## Guidance
    → Add a ## Guidance section. Topic documents require...

Warnings (1)
  context/area/_overview.md
    Topic not listed in overview: new-topic.md
    → Add new-topic.md to the Topics section

Info (1)
  context/other/old-topic.md
    Last validated 45 days ago
    → Document is getting stale

Token budget: 28,500 / 40,000 (3 areas)
  python-basics     18,200 (5 files)
  design-patterns    8,300 (3 files)
  testing            2,000 (1 file)
```

Severity groups only shown if they have issues. Suggestion lines prefixed
with `→`.

### JSON (`--json`)

Current behavior unchanged. Existing schema preserved.

## CLI Interface

```bash
# Summary (default)
python3 scripts/check_health.py --root .

# Detailed
python3 scripts/check_health.py --root . --detailed

# JSON (current behavior)
python3 scripts/check_health.py --root . --json

# Disable color
python3 scripts/check_health.py --root . --no-color
```

`--detailed` and `--json` are mutually exclusive.

## Module API

```python
# wos/formatting.py

def format_summary(report: dict, *, color: bool = False) -> str:
    """Render a compact one-line-per-issue health report."""

def format_detailed(report: dict, *, color: bool = False) -> str:
    """Render a severity-grouped health report with suggestions."""
```

Both take the same report dict that `check_health.py` already builds. Pure
functions, no side effects.

## Color

- Auto-detect TTY via `sys.stdout.isatty()`
- `--no-color` flag to force plain text
- Color mapping: FAIL = red, WARN = yellow, INFO = dim/gray, PASS = green
- Status line colored by worst severity
- Only severity labels and the status word are colored

## Changes

### 1. wos/formatting.py — New Module

- `format_summary()`: status line, one-line-per-issue, token budget line
- `format_detailed()`: status line, severity-grouped issues with suggestions,
  token budget with per-area breakdown
- ANSI color helpers (colorize by severity, strip when disabled)

### 2. scripts/check_health.py — CLI Updates

- Add `--detailed` flag (mutually exclusive with `--json`)
- Add `--json` flag (preserves current behavior)
- Add `--no-color` flag
- Default output calls `format_summary()`
- `--detailed` calls `format_detailed()`
- `--json` preserves current `json.dumps()` behavior

### 3. skills/health/SKILL.md — Update Examples

- Show text as default output format
- Note `--json` for programmatic use
- Update example output block

### 4. skills/health/references/health-check-workflow.md

Simplify to:
1. Run command (with `--no-color` for LLM context)
2. Show output directly
3. Suggest next steps based on exit code

### 5. skills/health/references/health-audit-workflow.md

- Simplify T1 portion to show text output
- T2 triggers still need LLM interpretation (unchanged)

### 6. tests/test_formatting.py — New Test File

- Test `format_summary()` with various issue combinations
- Test `format_detailed()` with severity grouping and suggestions
- Test color output includes ANSI codes
- Test no-color output is plain text
- Test clean report (0 issues)
- Test token budget rendering (summary and detailed)

### 7. tests/test_check_health_integration.py — Update Integration Tests

- Test `--json` preserves current behavior
- Test default output is text
- Test `--detailed` output
- Test `--no-color` flag

## Files Changed

| File | Change |
|------|--------|
| `wos/formatting.py` | New: format_summary, format_detailed, color helpers |
| `scripts/check_health.py` | Add --detailed, --json, --no-color; call formatters |
| `skills/health/SKILL.md` | Update output examples |
| `skills/health/references/health-check-workflow.md` | Simplify workflow |
| `skills/health/references/health-audit-workflow.md` | Simplify T1 portion |
| `tests/test_formatting.py` | New: formatting tests |
| `tests/test_check_health_integration.py` | Update for new CLI flags |

## Non-Goals

- Does not change validators, severity logic, or which checks run
- Does not add new validators
- Does not change Tier 2 trigger handling
- Does not add configurable color themes
- Does not add `--format` flag for extensible output formats
