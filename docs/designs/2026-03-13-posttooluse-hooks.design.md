---
name: PostToolUse Hooks for Frontmatter Validation and Timestamps
description: Two PostToolUse hooks that validate frontmatter and manage created_at/updated_at timestamps on markdown file writes
type: design
status: draft
related:
  - docs/research/2026-03-13-cross-platform-hooks.research.md
---

## Purpose

Provide automatic, advisory feedback when Claude writes or edits WOS-managed
markdown files. Two independent hooks fire on PostToolUse for Write and Edit
tools, inspecting the result and returning `additionalContext` so Claude
self-corrects in the same turn.

## Behavior

### File targeting

A file is hook-eligible when all three conditions are true:

1. Path ends with `.md`
2. File content starts with `---` (has frontmatter)
3. File is not gitignored (`git check-ignore -q <path>` exits non-zero)

Files that fail any condition are silently skipped (exit 0, no output).

### Hook 1: Frontmatter validation (`hook_validate_frontmatter.py`)

Parses frontmatter and checks:

- `name` field present and non-empty
- `description` field present and non-empty
- If `type: research`, `sources` field is non-empty
- If `type: context`, `related` field is present (warn-level)

On issues found, returns `additionalContext` describing each issue so
Claude can fix them. On no issues, exits silently.

Reuses `wos.frontmatter.parse_frontmatter()` for parsing. Does NOT
reuse `wos.validators` directly — the hook needs lightweight, fast
checks without importing the full validation stack (URL checking,
index sync, etc.).

### Hook 2: Timestamp management (`hook_manage_timestamps.py`)

Inspects frontmatter for timestamp fields:

- **New file** (Write tool, file didn't exist before): if `created_at`
  is missing, report it. If `updated_at` is missing, report it.
- **Existing file** (Edit tool, or Write to existing path): if
  `updated_at` is missing or doesn't match today's date, report it.

"Today's date" is UTC date in ISO 8601 format (YYYY-MM-DD).

On issues found, returns `additionalContext` with specific fix
instructions (e.g., "Add `created_at: 2026-03-13` to frontmatter").
On no issues, exits silently.

#### Detecting new vs existing file

The hook receives `tool_name` in the input JSON:

- `Write` tool = could be new or overwrite. The hook checks whether
  `created_at` already exists in the frontmatter. If absent, treat
  as new file needing `created_at`.
- `Edit` tool = always an existing file. Only check `updated_at`.

### I/O protocol

Both hooks follow the Claude Code command hook protocol:

- **Input:** JSON on stdin with `tool_name`, `tool_input` (containing
  `file_path` and `content` or edit fields), `tool_response`
- **Output:** JSON on stdout with `additionalContext` string when
  issues found. Empty/no output when clean.
- **Exit code:** Always 0 (advisory, never blocking)

### Registration

Hooks register in the plugin's `hooks/hooks.json` file:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python <plugin-scripts-dir>/hook_validate_frontmatter.py"
          },
          {
            "type": "command",
            "command": "python <plugin-scripts-dir>/hook_manage_timestamps.py"
          }
        ]
      }
    ]
  }
}
```

Both hooks run in parallel on every Write/Edit call. Non-markdown
files are filtered by the scripts themselves (fast path: check
file extension, exit immediately).

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `hook_validate_frontmatter.py` | `scripts/` | Frontmatter validation hook |
| `hook_manage_timestamps.py` | `scripts/` | Timestamp management hook |
| `hooks/hooks.json` | plugin root | Hook registration for Claude Code |
| `test_hook_validate_frontmatter.py` | `tests/` | Unit tests for validation hook |
| `test_hook_manage_timestamps.py` | `tests/` | Unit tests for timestamp hook |

## Constraints

- **Stdlib only.** No dependencies beyond what's in `wos/`.
- **Fast exit on non-targets.** Check `.md` extension before reading
  stdin fully or importing anything heavy.
- **No blocking.** Exit 0 always. Advisory context only.
- **No file mutation.** Hooks never write to the file. They report;
  Claude fixes.
- **Reuse `wos.frontmatter` only.** Do not import validators, document,
  url_checker, or other heavy modules.
- **Testable in isolation.** Each hook script exposes a pure function
  that takes parsed input and returns a result. The `if __name__`
  block handles stdin/stdout. Tests call the function directly.

## Acceptance Criteria

1. Writing a new `.md` file without `name` or `description` produces
   `additionalContext` mentioning the missing fields
2. Writing a new `.md` file without `created_at` produces context
   requesting the timestamp be added
3. Editing an existing `.md` file without updating `updated_at` to
   today produces context requesting the update
4. Non-`.md` files are silently skipped (no output, exit 0)
5. Gitignored `.md` files are silently skipped
6. Files without frontmatter (`---`) are silently skipped
7. Both hooks run without importing `wos.validators` or `wos.url_checker`
8. Each hook completes in <100ms for typical files
9. All tests pass with `pytest tests/test_hook_*.py -v`
