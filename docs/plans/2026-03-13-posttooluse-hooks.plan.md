---
name: PostToolUse Hooks for Frontmatter Validation and Timestamps
description: Implement two PostToolUse hooks that validate frontmatter and manage timestamps on markdown file writes
type: plan
status: approved
related:
  - docs/designs/2026-03-13-posttooluse-hooks.design.md
  - docs/research/2026-03-13-cross-platform-hooks.research.md
---

## Goal

Ship two PostToolUse command hooks that fire on Write/Edit tool calls,
providing advisory feedback when WOS-managed markdown files have
frontmatter issues or missing/stale timestamps.

## Scope

**Must have:**
- `hook_validate_frontmatter.py` — frontmatter validation
- `hook_manage_timestamps.py` — created_at/updated_at management
- `hooks/hooks.json` — plugin hook registration
- Unit tests for both hooks
- Both hooks follow existing script conventions (PEP 723, plugin root discovery)

**Won't have:**
- PreToolUse / input modification
- Blocking behavior (exit code 2)
- Index sync hooks
- Cross-platform hook configs beyond Claude Code
- File mutation by hooks

## Approach

Each hook script follows the same structure:

1. **Fast-path filter:** Extract `file_path` from stdin JSON, check `.md`
   extension. Exit 0 immediately if not markdown.
2. **Read file from disk** (PostToolUse means the file is already written).
3. **Gitignore check:** Run `git check-ignore -q <path>`. Exit 0 if ignored.
4. **Frontmatter check:** Verify file starts with `---`. Exit 0 if no frontmatter.
5. **Parse frontmatter** using `wos.frontmatter.parse_frontmatter()`.
6. **Run checks** specific to the hook's concern.
7. **Output JSON** with `additionalContext` if issues found, otherwise exit silently.

Scripts expose a pure `check()` function for testability. The `__main__`
block handles stdin/stdout plumbing. Tests call `check()` directly with
constructed dicts — no subprocess, no stdin mocking.

The `hooks/hooks.json` file registers both hooks under `PostToolUse` with
matcher `Write|Edit`. Claude Code runs matching hooks in parallel.

### Branch

`posttooluse-hooks`

## File Changes

| Action | File | Description |
|--------|------|-------------|
| Create | `scripts/hook_validate_frontmatter.py` | Frontmatter validation hook script |
| Create | `scripts/hook_manage_timestamps.py` | Timestamp management hook script |
| Create | `hooks/hooks.json` | Plugin hook registration |
| Create | `tests/test_hook_validate_frontmatter.py` | Tests for validation hook |
| Create | `tests/test_hook_manage_timestamps.py` | Tests for timestamp hook |

## Tasks

### Chunk 1: Hook scripts

- [ ] **Task 1: Create `hook_validate_frontmatter.py`**
  - Create `scripts/hook_validate_frontmatter.py` with PEP 723 metadata
    and standard plugin root discovery pattern (see `scripts/audit.py`).
  - Implement `check_frontmatter_issues(file_path: str, file_content: str) -> Optional[str]`
    that returns an `additionalContext` string or `None`.
  - Checks: `name` present+non-empty, `description` present+non-empty,
    `sources` non-empty when `type: research`, `related` present when
    `type: context`.
  - Implement `main()` that reads JSON from stdin, extracts `tool_input.file_path`,
    reads the file from disk, runs gitignore check, calls
    `check_frontmatter_issues()`, and prints JSON output.
  - Fast-path: exit 0 immediately if file_path doesn't end with `.md`.
  - Verify: `echo '{}' | python scripts/hook_validate_frontmatter.py` exits 0
    with no output.

- [ ] **Task 2: Create `hook_manage_timestamps.py`**
  - Create `scripts/hook_manage_timestamps.py` with same boilerplate.
  - Implement `check_timestamp_issues(tool_name: str, file_path: str, file_content: str, today: str) -> Optional[str]`
    that returns an `additionalContext` string or `None`. Accept `today`
    as parameter for testability (no date mocking needed).
  - Logic: For Write tool — if `created_at` absent, report both
    `created_at` and `updated_at` needed. For Edit tool — if `updated_at`
    absent or != today, report `updated_at` needed.
  - Implement `main()` with same stdin/filter/output pattern as Task 1.
    Pass `datetime.now(timezone.utc).strftime("%Y-%m-%d")` as `today`.
  - Verify: `echo '{}' | python scripts/hook_manage_timestamps.py` exits 0
    with no output.

- [ ] **Task 3: Create `hooks/hooks.json`**
  - Create `hooks/hooks.json` at plugin root with PostToolUse registration
    for both hooks, matcher `Write|Edit`.
  - Use `python ${CLAUDE_PLUGIN_ROOT}/scripts/hook_validate_frontmatter.py`
    and `python ${CLAUDE_PLUGIN_ROOT}/scripts/hook_manage_timestamps.py`
    as commands.
  - Verify: `python -m json.tool hooks/hooks.json` validates JSON.

### Chunk 2: Tests

- [ ] **Task 4: Create `test_hook_validate_frontmatter.py`**
  - Test `check_frontmatter_issues()` directly (no subprocess):
    - Valid frontmatter with all fields → returns `None`
    - Missing `name` → returns string mentioning "name"
    - Missing `description` → returns string mentioning "description"
    - Empty `name` → returns string mentioning "name"
    - Research type without sources → returns string mentioning "sources"
    - Context type without related → returns string mentioning "related"
    - Non-markdown file path → function not called (tested at main level)
    - File without frontmatter → returns `None`
    - Malformed frontmatter (no closing `---`) → returns `None` (graceful)
  - Verify: `python -m pytest tests/test_hook_validate_frontmatter.py -v`

- [ ] **Task 5: Create `test_hook_manage_timestamps.py`**
  - Test `check_timestamp_issues()` directly:
    - Write tool, no `created_at` → returns string mentioning "created_at"
    - Write tool, has `created_at`, no `updated_at` → returns string
      mentioning "updated_at"
    - Write tool, has both timestamps → returns `None`
    - Edit tool, no `updated_at` → returns string mentioning "updated_at"
    - Edit tool, `updated_at` is stale (not today) → returns string
      mentioning "updated_at"
    - Edit tool, `updated_at` matches today → returns `None`
    - File without frontmatter → returns `None`
  - Verify: `python -m pytest tests/test_hook_manage_timestamps.py -v`

- [ ] **Task 6: Run full test suite and lint**
  - Run `python -m pytest tests/ -v` — all tests pass
  - Run `ruff check scripts/hook_validate_frontmatter.py scripts/hook_manage_timestamps.py tests/test_hook_validate_frontmatter.py tests/test_hook_manage_timestamps.py` — no errors
  - Verify: both commands exit 0

## Validation

1. **Unit tests pass:**
   ```
   python -m pytest tests/test_hook_validate_frontmatter.py tests/test_hook_manage_timestamps.py -v
   ```
   Expected: all tests pass.

2. **Fast-path performance:** Non-markdown files produce no output and exit 0:
   ```
   echo '{"tool_name":"Write","tool_input":{"file_path":"foo.py"}}' | python scripts/hook_validate_frontmatter.py
   echo '{"tool_name":"Write","tool_input":{"file_path":"foo.py"}}' | python scripts/hook_manage_timestamps.py
   ```
   Expected: exit 0, no stdout.

3. **Frontmatter validation fires on bad files:**
   Create a temp `.md` file with empty `name`, pipe a PostToolUse JSON
   pointing to it. Expected: JSON output with `additionalContext`
   mentioning "name".

4. **Timestamp hook fires on missing timestamps:**
   Create a temp `.md` file without `created_at`, pipe a Write-tool JSON.
   Expected: JSON output with `additionalContext` mentioning "created_at".

5. **hooks.json is valid JSON:**
   ```
   python -m json.tool hooks/hooks.json
   ```

6. **No heavy imports:**
   ```
   python -c "import ast, sys; tree=ast.parse(open('scripts/hook_validate_frontmatter.py').read()); imports=[n.names[0].name if isinstance(n,ast.Import) else n.module for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]; assert 'wos.validators' not in imports and 'wos.url_checker' not in imports, f'Heavy import found: {imports}'"
   ```

7. **Full test suite still passes:**
   ```
   python -m pytest tests/ -v
   ```
