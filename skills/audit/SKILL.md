---
name: audit
description: >
  This skill should be used when the user asks to "check health",
  "validate documents", "run validation", "audit content quality",
  "review documents", "check coverage", "check freshness",
  "run health check", or "what needs attention".
argument-hint: "[check|audit|review|coverage|freshness]"
user-invocable: true
---

# Audit Skill

Observe and report on project content quality. Read-only -- reports but
does not modify any files (unless `--fix` is used for index regeneration).

## How to Run

**Prerequisite:** Follow the preflight check in the [preflight reference](../_shared/references/preflight.md) before running.

```bash
# Default: run all checks including URL reachability
uv run <plugin-scripts-dir>/audit.py --root .

# Skip URL reachability checks (fast, offline-friendly)
uv run <plugin-scripts-dir>/audit.py --root . --no-urls

# Validate a single file
uv run <plugin-scripts-dir>/audit.py path/to/file.md --root . --no-urls

# JSON output for programmatic use
uv run <plugin-scripts-dir>/audit.py --root . --json

# Auto-fix out-of-sync or missing _index.md files
uv run <plugin-scripts-dir>/audit.py --root . --fix

# Exit 1 on any issue (including warnings)
uv run <plugin-scripts-dir>/audit.py --root . --strict

# Custom word count threshold for context files (default: 800)
uv run <plugin-scripts-dir>/audit.py --root . --context-max-words 500
```

Exit code: 1 if any `fail`, 0 if only `warn`. Use `--strict` to exit 1 on any issue.

## The Checks

### 1. Frontmatter Validation (fail + warn)

Verifies:
- **fail:** `name` and `description` are non-empty
- **fail:** `type: research` documents have a non-empty `sources` list
- **warn:** Source items should be URL strings, not dicts
- **warn:** Context files should have `related` fields

### 2. Content Length (warn)

Warns when context files exceed 800 words (configurable via `--context-max-words`).
Artifacts and `_index.md` files are excluded.

### 3. Source URL Reachability (fail)

Checks that every URL in `sources` is reachable via HTTP.
Skipped with `--no-urls`.

### 4. Related Path Validation (fail)

Checks that local file paths in `related` exist on disk.

### 5. Index Sync (fail + warn)

- **fail:** `_index.md` missing or out of sync
- **warn:** `_index.md` has no area description (preamble)

## Interpreting Results

Summary line first, then table:

```
2 fail, 1 warn across 15 files

file                              | sev  | issue
context/api/auth.md               | fail | Frontmatter 'name' is empty
context/api/_index.md             | warn | Index has no area description (preamble)
```

Exit code: 1 if any `fail`, 0 if only `warn`. Use `--strict` to exit 1 on any issue.

With `--json`, output is a JSON array of objects:

```json
[
  {
    "file": "context/area/topic.md",
    "issue": "Frontmatter 'name' is empty",
    "severity": "fail"
  }
]
```

A clean project produces:

```
All checks passed.
```

## Key Rules

- Audit is read-only (except `--fix` which only regenerates `_index.md` files)
- Use `/wos:create` to create missing documents
- Empty project (no `context/` or `artifacts/`) exits 0 with no issues
