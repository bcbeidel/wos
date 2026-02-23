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

```bash
# Default: run all checks including URL reachability
python3 scripts/audit.py --root .

# Skip URL reachability checks (fast, offline-friendly)
python3 scripts/audit.py --root . --no-urls

# JSON output for programmatic use
python3 scripts/audit.py --root . --json

# Auto-fix out-of-sync or missing _index.md files
python3 scripts/audit.py --root . --fix
```

Exit code: 0 if no issues, 1 if any issues found.

## The 5 Checks

### 1. Frontmatter Validation

Verifies that every document has non-empty `name` and `description` fields
in its YAML frontmatter.

**Failure:** `Frontmatter 'name' is empty` or `Frontmatter 'description' is empty`
**Fix:** Add or fill in the missing frontmatter field.

### 2. Research Sources

Verifies that documents with `type: research` have a non-empty `sources` list.

**Failure:** `Research document has no sources`
**Fix:** Add a `sources:` list with at least one verified URL to the frontmatter.

### 3. Source URL Reachability

Checks that every URL in a document's `sources` list is reachable via HTTP.
Skipped when `--no-urls` is passed.

**Failure:** `Source URL unreachable: <url> (<reason>)`
**Fix:** Replace the dead URL with a working one, or remove it if the source
no longer exists.

### 4. Related Path Validation

Checks that every local file path in a document's `related` list exists on
disk. URLs (http/https) are skipped -- only file paths are validated.

**Failure:** `Related path does not exist: <path>`
**Fix:** Correct the path, or remove the entry if the related file was deleted.

### 5. Index Sync

Checks that every directory containing markdown files has an `_index.md` that
accurately lists all files and subdirectories.

**Failure:** `_index.md missing` or `_index.md out of sync`
**Fix:** Run `python3 scripts/audit.py --root . --fix` to regenerate, or
run `python3 scripts/reindex.py --root .` to regenerate all indexes.

## Interpreting Results

Each issue is reported as:

```
[FAIL] <file>: <issue description>
```

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

All issues have severity `fail`. A clean project produces:

```
All checks passed.
```

## Key Rules

- Audit is read-only (except `--fix` which only regenerates `_index.md` files)
- Use `/wos:create` to create missing documents
- Empty project (no `context/` or `artifacts/`) exits 0 with no issues
